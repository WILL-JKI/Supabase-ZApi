import os
import dotenv
dotenv.load_dotenv()
import supabase
import requests

# Configuração do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# Configuração do Z-API
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")

# Verifica se todas as variáveis de ambiente estão configuradas
if not all([SUPABASE_URL, SUPABASE_KEY, ZAPI_INSTANCE_ID, ZAPI_TOKEN]):
    print("Erro: Variáveis de ambiente não configuradas corretamente.")
    print("Por favor, configure o arquivo .env com as credenciais.")
    exit(1)

try:
    supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
    ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text"
    
    # Busca apenas os contatos com status 'pendente'
    contatos_response = supabase_client.table('contatos').select('*').eq('status', 'pendente').execute()
    contatos = contatos_response.data
    
    if not contatos:
        print("Nenhum contato pendente encontrado no Supabase.")
        print("Verifique se as políticas de RLS (Row Level Security) estão configuradas corretamente para permitir leitura.")
        exit(0)
    
    print(f"Encontrados {len(contatos)} contatos pendentes para enviar mensagens.")
    
    for contato in contatos:
        nome = contato.get('nome')
        numero = contato.get('numero')
        status = contato.get('status')
        
        if not nome or not numero or status != 'pendente':
            print(f"Contato com dados incompletos ou já processado: {contato}")
            continue
        
        # Monta a mensagem
        mensagem = f"Olá, {nome} tudo bem com você?"
        
        # Organiza os dados no formato que a Z-API precisa
        payload = {
            "phone": numero,
            "message": mensagem
        }
        
        # Envia a mensagem para a Z-API
        response = requests.post(ZAPI_URL, json=payload)
        
        # Verifica se a requisição foi bem-sucedida
        if response.status_code == 200:
            print(f"Mensagem enviada para {numero} com sucesso!")
            # Atualiza para 'enviado' no Supabase
            supabase_client.table('contatos').update({'status': 'enviado'}).eq('id', contato['id']).execute()
        else:
            print(f"Erro ao enviar para {numero}: {response.text}")
            # Atualiza para 'erro' no Supabase
            supabase_client.table('contatos').update({'status': 'erro'}).eq('id', contato['id']).execute()
            
except Exception as e:
    print(f"Ocorreu um erro: {str(e)}")
