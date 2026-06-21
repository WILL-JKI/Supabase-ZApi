import os
import sys
import argparse
import requests
import dotenv
import supabase
from loguru import logger


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def configurar_logging():
    """Configura o loguru: formato colorido no terminal e arquivo de log rotativo."""
    logger.remove()  # remove o handler padrão

    fmt_terminal = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{function}</cyan> - <level>{message}</level>"
    )
    fmt_arquivo = (
        "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {function} - {message}"
    )

    logger.add(sys.stderr, format=fmt_terminal, level="DEBUG", colorize=True)
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        format=fmt_arquivo,
        level="INFO",
        rotation="1 day",
        retention="7 days",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

def carregar_configuracoes() -> dict:
    """Carrega e valida as variáveis de ambiente. Encerra o programa em caso de erro."""
    dotenv.load_dotenv()

    config = {
        "supabase_url": os.getenv("SUPABASE_URL"),
        "supabase_key": os.getenv("SUPABASE_KEY"),
        "zapi_instance_id": os.getenv("ZAPI_INSTANCE_ID"),
        "zapi_token": os.getenv("ZAPI_TOKEN"),
        # Opcional: necessário apenas se o "Token de Segurança" estiver ativado na instância Z-API
        "zapi_client_token": os.getenv("ZAPI_CLIENT_TOKEN"),
    }

    # zapi_client_token é opcional, não entra na validação de obrigatórios
    obrigatorios = ["supabase_url", "supabase_key", "zapi_instance_id", "zapi_token"]
    faltando = [chave for chave in obrigatorios if not config.get(chave)]
    if faltando:
        logger.error("Variáveis de ambiente ausentes: {}", ", ".join(faltando))
        logger.error("Configure o arquivo .env com as credenciais e tente novamente.")
        sys.exit(1)

    config["zapi_url"] = (
        f"https://api.z-api.io/instances/{config['zapi_instance_id']}"
        f"/token/{config['zapi_token']}/send-text"
    )

    logger.debug("Configurações carregadas com sucesso.")
    return config


# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------

def conectar_supabase(config: dict) -> supabase.Client:
    """Cria e retorna o client do Supabase."""
    client = supabase.create_client(config["supabase_url"], config["supabase_key"])
    logger.debug("Conexão com o Supabase estabelecida.")
    return client


def buscar_contatos_pendentes(client: supabase.Client) -> list[dict]:
    """Busca e retorna todos os contatos com status 'pendente'."""
    resposta = client.table("contatos").select("*").eq("status", "pendente").execute()
    contatos = resposta.data

    if not contatos:
        logger.warning("Nenhum contato pendente encontrado.")
        logger.warning(
            "Possíveis causas:\n"
            "  1) Todos os contatos já foram processados (status 'enviado' ou 'erro').\n"
            "     -> Para resetar, execute: python main.py --reset\n"
            "  2) A tabela está vazia ou as políticas de RLS bloqueiam a leitura.\n"
            "     -> Verifique as políticas de RLS no painel do Supabase."
        )
        return []

    logger.info("Encontrados {} contato(s) pendente(s).", len(contatos))
    return contatos


def atualizar_status(client: supabase.Client, contato_id: int, status: str):
    """Atualiza o status de um contato específico no Supabase."""
    client.table("contatos").update({"status": status}).eq("id", contato_id).execute()
    logger.debug("Contato id={} atualizado para status='{}'.", contato_id, status)


def resetar_contatos(client: supabase.Client):
    """Reseta todos os contatos para o status 'pendente'."""
    logger.info("Iniciando reset de todos os contatos para 'pendente'...")
    resposta = (
        client.table("contatos")
        .update({"status": "pendente"})
        .neq("id", 0)
        .execute()
    )
    logger.success(
        "Reset concluído. {} registro(s) atualizado(s).", len(resposta.data)
    )


# ---------------------------------------------------------------------------
# Z-API
# ---------------------------------------------------------------------------

def enviar_mensagem(config: dict, contato: dict) -> bool:
    """
    Monta e envia a mensagem via Z-API.
    Retorna True em caso de sucesso, False em caso de erro.
    """
    nome = contato.get("nome")
    numero = contato.get("numero")

    if not nome or not numero:
        logger.warning("Contato com dados incompletos ignorado: {}", contato)
        return False

    mensagem = f"Olá, {nome} tudo bem com você?"
    payload = {"phone": numero, "message": mensagem}

    headers = {}
    if config.get("zapi_client_token"):
        headers["Client-Token"] = config["zapi_client_token"]

    resposta = requests.post(config["zapi_url"], json=payload, headers=headers)

    if resposta.status_code == 200:
        logger.success("Mensagem enviada para {} ({}).", nome, numero)
        return True
    else:
        logger.error(
            "Falha ao enviar para {} ({}). Status: {} — {}",
            nome,
            numero,
            resposta.status_code,
            resposta.text,
        )
        return False


# ---------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------

def processar_envios(client: supabase.Client, config: dict):
    """Busca contatos pendentes e orquestra o envio e atualização de status."""
    contatos = buscar_contatos_pendentes(client)
    if not contatos:
        return

    enviados = 0
    erros = 0

    for contato in contatos:
        sucesso = enviar_mensagem(config, contato)
        novo_status = "enviado" if sucesso else "erro"
        atualizar_status(client, contato["id"], novo_status)

        if sucesso:
            enviados += 1
        else:
            erros += 1

    logger.info(
        "Processamento concluído. Enviados: {} | Erros: {}.", enviados, erros
    )


# ---------------------------------------------------------------------------
# Tabelas
# ---------------------------------------------------------------------------

def criar_tabelas():
    """
    Exibe o SQL necessário para criar a estrutura de tabelas no Supabase.
    Execute este SQL no Dashboard do Supabase: https://supabase.com/dashboard
    """
    sql = """
-- Execute no SQL Editor do Supabase Dashboard:
-- https://supabase.com/dashboard > SQL Editor > New query

CREATE TABLE IF NOT EXISTS contatos (
    id        BIGSERIAL    PRIMARY KEY,
    nome      TEXT         NOT NULL,
    numero    TEXT         NOT NULL,
    status    TEXT         NOT NULL DEFAULT 'pendente'
                           CHECK (status IN ('pendente', 'enviado', 'erro')),
    criado_em TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Habilitar Row Level Security (RLS)
ALTER TABLE contatos ENABLE ROW LEVEL SECURITY;

-- Politica unica: permitir todas as operacoes (SELECT, INSERT, UPDATE, DELETE)
CREATE POLICY "acesso total" ON contatos
    FOR ALL
    USING (true)
    WITH CHECK (true);
"""
    logger.info("SQL para criacao de tabelas:")
    print(sql)


def popular_tabelas(client: supabase.Client):
    """Insere contatos de exemplo na tabela para facilitar testes."""
    contatos_exemplo = [
        {"nome": "Alice Silva",  "numero": "5511999990001", "status": "pendente"},
        {"nome": "Bruno Costa",  "numero": "5511999990002", "status": "pendente"},
        {"nome": "Carla Mendes", "numero": "5511999990003", "status": "pendente"},
    ]

    logger.info("Inserindo {} contatos de exemplo...", len(contatos_exemplo))
    try:
        resposta = client.table("contatos").insert(contatos_exemplo).execute()
        logger.success("{} contato(s) inserido(s) com sucesso.", len(resposta.data))
    except Exception as e:
        if "row-level security" in str(e).lower() or "42501" in str(e):
            logger.error("Sem permissao de INSERT na tabela 'contatos' (RLS bloqueando).")
            logger.error(
                "Para corrigir, execute no SQL Editor do Supabase:\n\n"
                "  CREATE POLICY \"acesso total\" ON contatos\n"
                "      FOR ALL USING (true) WITH CHECK (true);\n\n"
                "Ou rode: python main.py --criar-tabelas  (e aplique o SQL completo)"
            )
        else:
            logger.error("Erro ao inserir contatos de exemplo: {}", e)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def main():
    configurar_logging()

    parser = argparse.ArgumentParser(
        description="SupaBase + Z-API: disparo de mensagens via WhatsApp"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reseta todos os contatos para status 'pendente'.",
    )
    parser.add_argument(
        "--criar-tabelas",
        action="store_true",
        help="Exibe o SQL para criação das tabelas no Dashboard do Supabase.",
    )
    parser.add_argument(
        "--popular-tabelas",
        action="store_true",
        help="Insere contatos de exemplo na tabela 'contatos'.",
    )
    args = parser.parse_args()

    # --criar-tabelas não precisa de conexão
    if args.criar_tabelas:
        criar_tabelas()
        return

    config = carregar_configuracoes()
    client = conectar_supabase(config)

    if args.reset:
        resetar_contatos(client)
    elif args.popular_tabelas:
        popular_tabelas(client)
    else:
        processar_envios(client, config)


if __name__ == "__main__":
    main()
