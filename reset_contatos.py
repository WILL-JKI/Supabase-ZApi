import os
import dotenv
dotenv.load_dotenv()
import supabase

# Configuração do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Verifica se as variáveis estão configuradas
if not SUPABASE_URL or not SUPABASE_KEY:
    print("Erro: Variáveis de ambiente não configuradas corretamente.")
    print("Por favor, configure o arquivo .env com as credenciais.")
    exit(1)

try:
    supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Atualiza todos os contatos para status 'pendente'
    response = supabase_client.table('contatos').update({'status': 'pendente'}).neq('id', 0).execute()
    
    print(f"Contatos resetados com sucesso! Total de registros atualizados: {len(response.data)}")
    
except Exception as e:
    print(f"Ocorreu um erro: {str(e)}")
