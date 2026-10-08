# Setup — AWS Academy Learner Lab

Usado nas Aulas 2 (deploy), 4 (canary), 5 (MLflow, e Bedrock se estiver liberado) e **6 (deploy do agente do capstone)**.
O AWS Academy é a plataforma **prioritária** da disciplina.

> **Este roteiro não foi testado contra um Learner Lab real.** Os limites abaixo vêm da lista
> oficial de serviços do Learner Lab e do guia do educador (ambos em `02_Apoio_Referencia/05_AWS_Academy/`),
> que são de 2021 e podem ter mudado. A primeira pessoa a rodar deve conferir cada passo.

## O que o Learner Lab permite (e o que atrapalha)

| Limite | Efeito nos laboratórios |
|---|---|
| Só `us-east-1` e `us-west-2` | Todos os scripts usam `us-east-1` |
| Sessão de **4 horas**; credenciais novas a cada "Start Lab" | O GitHub Actions precisa dos secrets atualizados **a cada deploy** (passo 3). **Os recursos continuam no ar** entre as sessões (veja o passo 4) |
| IAM quase bloqueado: sem criar usuário, role ou provedor OIDC | Só existem a `LabRole` e a `LabInstanceProfile`; o Actions não consegue usar OIDC |
| Crédito de US$ 100 por aluno | Lambda, ECR e S3 custam centavos; **pare o EC2 do MLflow** ao fim da aula |
| EC2 só `nano` a `large`; Lambda, ECR, S3, SSM, CloudWatch, Secrets Manager liberados | Cabe nos labs |
| Bedrock, ECS e EKS **não aparecem** na lista de 2021 do *Learner Lab – Foundation Services* | Confira no console antes da Aula 5. Há também o *Learner Lab – Associate Services* (só para educador credenciado em um curso de nível associate), com lista mais ampla: o professor deve conferir qual variante a turma usa. Se o Bedrock não aparecer, use Ollama ou um endpoint OpenAI-compatível (veja `agente/llm.py`) |
| Cursos de IA/CI-CD da própria AWS Academy | O portal tem o *Lab Project – Microservices and CI/CD Pipeline Builder* e o *Cloud Developing*: vale conferir se complementam as Aulas 2 e 4 |

## Uso permitido

O programa AWS Academy **proíbe** usar o laboratório para mineração de criptomoeda, análise de pacotes de rede
(*sniffing*), testes de intrusão e *ethical hacking*, e as credenciais são pessoais (não compartilhe o seu login
do portal). Nada deste curso precisa disso. Os recursos servem a **este curso**, enquanto a turma estiver aberta.

## 1. Primeiro acesso (faça antes da aula)

1. Entre no AWS Academy → o curso **Learner Lab** → **Launch AWS Academy Learner Lab**.
2. **Start Lab** e espere a bolinha ficar verde. **AWS** abre o console.
3. No console, procure por cada serviço que vamos usar e veja se abre sem erro de acesso:
   **Lambda**, **ECR**, **S3**, **EC2**, **Systems Manager**, **Bedrock** (este é o que mais varia).
4. Anote o resultado — define o provedor de LLM da Aula 5 (`bedrock` ou `openai`/Ollama).

## 2. Credenciais para o terminal (Codespaces)

No Learner Lab, clique em **AWS Details → AWS CLI → Show** e copie o bloco. No terminal do Codespaces:

```bash
mkdir -p ~/.aws && cat > ~/.aws/credentials   # cole o bloco [default] e termine com Ctrl+D
export AWS_REGION=us-east-1
aws sts get-caller-identity                   # deve mostrar a LabRole
```

## 3. Credenciais para o GitHub Actions (a cada aula)

Os três valores mudam a cada "Start Lab". No repositório: **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Valor (de AWS Details → AWS CLI) |
|---|---|
| `AWS_ACCESS_KEY_ID` | `aws_access_key_id` |
| `AWS_SECRET_ACCESS_KEY` | `aws_secret_access_key` |
| `AWS_SESSION_TOKEN` | `aws_session_token` |

Pelo `gh`, mais rápido (com as variáveis já exportadas no terminal):

```bash
gh secret set AWS_ACCESS_KEY_ID     --body "$(aws configure get aws_access_key_id)"
gh secret set AWS_SECRET_ACCESS_KEY --body "$(aws configure get aws_secret_access_key)"
gh secret set AWS_SESSION_TOKEN     --body "$(aws configure get aws_session_token)"
```

Crie também o environment `producao` (Settings → Environments) — os workflows de deploy o usam.

**Se o workflow falhar com "Credenciais do Academy expiradas":** o lab foi reiniciado. Repita este passo.

## 4. O capstone (Aula 6) também fica no Academy

O guia do educador diz que *"services deployed by students are available until the end date designated by the
educator"* e que, ao encerrar a sessão, o "End Lab" só **para as EC2**: os demais recursos continuam
disponíveis. Então uma função **Lambda** com Function URL **continua no ar entre as sessões**; só as
credenciais expiram, e você só precisa de credenciais novas **na hora de fazer um novo deploy**. Por isso o
agente vai para o Lambda por padrão (workflow **Aula 6 · Deploy do agente (AWS Lambda)**).

Cuidados:

- **Não hospede o agente numa EC2**: ela é parada no "End Lab" e o IP muda ao reiniciar.
- **O LLM em produção** vem de uma destas fontes (variável `AGENTE_LLM_PROVEDOR`): `bedrock` (se o seu Learner
  Lab liberar e a `LabRole` puder invocar o modelo), `openai` (um endpoint compatível, como o Foundry/Azure OpenAI
  ou outro, com `AGENTE_LLM_BASE_URL`, `AGENTE_LLM_MODELO` e o secret `AGENTE_LLM_API_KEY`) ou `simulado`
  (só para provar o deploy). O Ollama não roda no Lambda.
- O crédito de US$ 100 cobre sobrando o Lambda e o ECR do capstone; o gasto aparece no topo do laboratório
  (com atraso de até 8 h).
- O **Azure Web Apps** continua disponível como alternativa (`roteiros/setup-azure.md`), com as regras de região
  da parceria Microsoft × FIAP.

## 5. Limpeza ao fim

```bash
mlops/servidor-mlflow-ec2.sh destruir     # EC2, security group e bucket do MLflow
aws lambda delete-function --function-name classificador-avaliacoes
aws ecr delete-repository --repository-name classificador-avaliacoes --force
aws lambda delete-function --function-name agente-atendimento
aws ecr delete-repository --repository-name agente-atendimento --force
```
