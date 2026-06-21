# Supabase-ZApi 🚀

Código em Python que lê pessoas cadastradas no Supabase e envia mensagens personalizadas via Z-API (WhatsApp).

## Configuração do Ambiente ⚙️

### Criação do Ambiente Virtual

```bash
python -m venv venv
```

### Variáveis de Ambiente

As credenciais e configurações sensíveis são armazenadas em um arquivo `.env` (ignorado pelo Git por segurança). Crie um arquivo `.env` na raiz do projeto com a seguinte estrutura (utilize o arquivo `.env.example` como referência):

```plaintext
SUPABASE_URL=sua_url_do_supabase
SUPABASE_KEY=sua_chave_anon_do_supabase
ZAPI_INSTANCE_ID=seu_id_da_instancia_zapi
ZAPI_TOKEN=seu_token_da_zapi
ZAPI_CLIENT_TOKEN=seu_token_de_seguranca_zapi  # opcional, veja instruções abaixo
```

#### Obtendo as credenciais do Supabase:
1. Acesse o painel do Supabase
2. Vá para **Project Overview**
3. Copie a **URL** do projeto e use como `SUPABASE_URL`
4. Vá para **Project Overview > API Keys**
5. Encontre a seção **Legacy anon, service_role API keys**
6. Copie a chave **anon public** e use como `SUPABASE_KEY`

#### Obtendo as credenciais da Z-API:
1. Acesse o painel da Z-API
2. Vá para a página da sua instância
3. Copie o **Instance ID** e use como `ZAPI_INSTANCE_ID`
4. Copie o **Token** e use como `ZAPI_TOKEN`

#### Token de Segurança Z-API (`ZAPI_CLIENT_TOKEN`) — opcional:

Caso receba o erro `{"error":"your client-token is not configured"}`, sua instância tem o **Token de Segurança** ativado. Para configurar:

1. Acesse o painel da Z-API → sua instância → aba **Segurança**
2. Copie o **Token de Segurança** exibido
3. Adicione ao `.env`:
   ```plaintext
   ZAPI_CLIENT_TOKEN=seu_token_de_seguranca_aqui
   ```

> Para desativar esse requisito, basta ir em **Segurança** na Z-API e desabilitar o Token de Segurança. Se `ZAPI_CLIENT_TOKEN` não estiver no `.env`, o código funciona normalmente sem ele.

## Configuração do Supabase 🗄️

### Criação da Tabela de Contatos

Execute o comando abaixo para obter o SQL de criação da tabela direto no terminal:

```bash
python main.py --criar-tabelas
```

O SQL exibido deve ser executado no **SQL Editor** do painel do Supabase. A tabela gerada terá a seguinte estrutura:

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | BIGSERIAL | Chave primária, gerada automaticamente |
| `nome` | TEXT | Nome do contato |
| `numero` | TEXT | Número de WhatsApp (ex: `5511999990001`) |
| `status` | TEXT | `pendente`, `enviado` ou `erro` |
| `criado_em` | TIMESTAMPTZ | Data de criação (preenchida automaticamente) |

#### Inserindo contatos de exemplo:

```bash
python main.py --popular-tabelas
```

Isso insere 3 contatos de teste com status `pendente` para validar o fluxo.

Você também pode inserir contatos manualmente via **Table Editor** no painel do Supabase.

### Políticas de Segurança RLS (Row Level Security)

O SQL gerado por `--criar-tabelas` já inclui a política de RLS recomendada para uso com `service_role`. Caso prefira configurar manualmente:

```sql
-- Política para leitura
CREATE POLICY "Permitir leitura publica em contatos"
ON contatos FOR SELECT USING (true);

-- Política para atualização
CREATE POLICY "Permitir atualizacao publica em contatos"
ON contatos FOR UPDATE USING (true);
```

## Como Executar o Projeto ▶️

Ative o ambiente virtual:

- No Windows:
  ```bash
  venv\Scripts\activate
  ```

- No Linux/Mac:
  ```bash
  source venv/bin/activate
  ```

Instale as dependências:

```bash
pip install -r requirements.txt
```

### Comandos disponíveis

| Comando | Descrição |
|---|---|
| `python main.py` | Envia mensagens para todos os contatos com status `pendente` |
| `python main.py --reset` | Reseta todos os contatos para status `pendente` |
| `python main.py --criar-tabelas` | Exibe o SQL de criação da tabela para rodar no Dashboard |
| `python main.py --popular-tabelas` | Insere contatos de exemplo para testes |
| `python main.py --help` | Exibe a ajuda com todos os comandos disponíveis |

## Logs 📋

O projeto utiliza **loguru** para logging profissional:

- **Terminal**: logs coloridos por nível (INFO, WARNING, ERROR, SUCCESS)
- **Arquivo**: logs salvos em `logs/app_YYYY-MM-DD.log` com rotação diária e retenção de 7 dias
