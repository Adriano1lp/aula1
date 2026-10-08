#!/usr/bin/env bash
# Aula 5 — sobe um servidor MLflow num EC2 do AWS Academy (Learner Lab).
#
#   mlops/servidor-mlflow-ec2.sh           # cria (ou reaproveita) a instância
#   mlops/servidor-mlflow-ec2.sh destruir  # remove instância, security group e bucket
#
# NÃO TESTADO contra o Learner Lab real — rode primeiro com a sua conta e ajuste.
# Pré-requisito: credenciais do lab no ambiente (roteiros/setup-aws-academy.md).
#
# Decisões:
# - t3.small: dentro do limite do Learner Lab (nano a large) e sobra memória para o MLflow.
# - LabInstanceProfile: o EC2 grava os artefatos no S3 sem chave nenhuma na máquina.
# - Backend de metadados em SQLite no disco da instância; artefatos no S3.
# - O security group libera a porta 5000 SÓ para o seu IP público atual.
#   Se o seu IP mudar (outra rede), rode o script de novo para atualizar a regra.
# - O IP público muda quando o lab é parado e iniciado: o script imprime o endereço novo.
set -euo pipefail

export AWS_REGION="${AWS_REGION:-us-east-1}" AWS_DEFAULT_REGION="${AWS_REGION:-us-east-1}"
NOME="mlflow-aie"
CONTA=$(aws sts get-caller-identity --query Account --output text)
BUCKET="mlflow-aie-$CONTA"

if [[ "${1:-}" == "destruir" ]]; then
  ID=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=$NOME" "Name=instance-state-name,Values=pending,running,stopped" \
    --query 'Reservations[].Instances[].InstanceId' --output text)
  [[ -n "$ID" ]] && aws ec2 terminate-instances --instance-ids $ID >/dev/null && aws ec2 wait instance-terminated --instance-ids $ID
  SG=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$NOME" --query 'SecurityGroups[0].GroupId' --output text)
  [[ "$SG" != "None" ]] && aws ec2 delete-security-group --group-id "$SG"
  aws s3 rb "s3://$BUCKET" --force 2>/dev/null || true
  echo "Removido."
  exit 0
fi

MEU_IP=$(curl -s https://checkip.amazonaws.com | tr -d '\n')

# Bucket de artefatos
aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null || aws s3 mb "s3://$BUCKET" >/dev/null

# Security group: porta 5000 só para o seu IP
SG=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$NOME" --query 'SecurityGroups[0].GroupId' --output text)
if [[ "$SG" == "None" ]]; then
  VPC=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
  SG=$(aws ec2 create-security-group --group-name "$NOME" --description "MLflow do laboratorio" --vpc-id "$VPC" \
    --query GroupId --output text)
fi
aws ec2 revoke-security-group-ingress --group-id "$SG" --protocol tcp --port 5000 --cidr 0.0.0.0/0 >/dev/null 2>&1 || true
aws ec2 authorize-security-group-ingress --group-id "$SG" --protocol tcp --port 5000 --cidr "$MEU_IP/32" >/dev/null 2>&1 || true

ID=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=$NOME" "Name=instance-state-name,Values=pending,running,stopped" \
  --query 'Reservations[].Instances[].InstanceId' --output text)

if [[ -z "$ID" ]]; then
  AMI=$(aws ssm get-parameter --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
    --query Parameter.Value --output text)
  USERDATA=$(cat <<FIM
#!/bin/bash
dnf install -y python3.12 python3.12-pip
python3.12 -m venv /opt/mlflow
/opt/mlflow/bin/pip install mlflow==3.16.1 boto3
cat > /etc/systemd/system/mlflow.service <<UNIT
[Unit]
Description=MLflow
After=network.target
[Service]
ExecStart=/opt/mlflow/bin/mlflow server --host 0.0.0.0 --port 5000 --allowed-hosts "*" \
  --backend-store-uri sqlite:////opt/mlflow/mlflow.db --artifacts-destination s3://$BUCKET
Restart=always
Environment=AWS_DEFAULT_REGION=$AWS_REGION
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload && systemctl enable --now mlflow
FIM
)
  ID=$(aws ec2 run-instances --image-id "$AMI" --instance-type t3.small --security-group-ids "$SG" \
    --iam-instance-profile Name=LabInstanceProfile --user-data "$USERDATA" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NOME}]" \
    --query 'Instances[0].InstanceId' --output text)
  echo "Instância $ID criada; a instalação leva ~2 min." >&2
else
  aws ec2 start-instances --instance-ids "$ID" >/dev/null 2>&1 || true
fi

aws ec2 wait instance-running --instance-ids "$ID"
IP=$(aws ec2 describe-instances --instance-ids "$ID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

echo "Esperando o MLflow responder em http://$IP:5000 ..." >&2
for _ in $(seq 1 40); do curl -sf "http://$IP:5000/health" >/dev/null && break; sleep 10; done

cat <<FIM

✅ MLflow no ar
   Interface:  http://$IP:5000
   Para usar:  export MLFLOW_TRACKING_URI=http://$IP:5000
   Artefatos:  s3://$BUCKET
FIM
