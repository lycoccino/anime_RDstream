import os
import sys
import requests
import subprocess
import urllib.parse
import re
import time
import socket
import cloudscraper
# Use the real package instead of the vendored path
from urllib3.util import connection as urllib3_cn
from bs4 import BeautifulSoup
import warnings
import shutil # <--- Importante para checar se o programa existe
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich.panel import Panel
from rich import box

# --- 🛑 HACK DE PERFORMANCE: FORÇAR IPV4 🛑 ---
def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family
# -----------------------------------------------

# --- CHECK DE DEPENDÊNCIAS ---
def check_system_dependencies():
    """Verifica se o MPV está instalado e acessível."""
    if not shutil.which("mpv"):
        console.print(Panel(
            "[bold red]❌ MPV NÃO ENCONTRADO![/bold red]\n\n"
            "O script precisa do player [bold]MPV[/bold] para rodar.\n"
            "O Python não consegue instalá-lo sozinho.\n\n"
            "[bold cyan]Linux (Ubuntu/Debian):[/bold cyan]\n"
            "   sudo apt install mpv\n\n"
            "[bold cyan]Windows:[/bold cyan]\n"
            "   1. Baixe em: https://mpv.io/installation/\n"
            "   2. Descompacte.\n"
            "   3. [bold red]IMPORTANTE:[/bold red] Adicione a pasta do mpv.exe ao seu PATH do Windows.\n"
            "      (Ou jogue o mpv.exe dentro da pasta deste script)",
            title="Dependência Faltando", border_style="red"
        ))
        sys.exit(1)

console = Console()
warnings.filterwarnings("ignore")

# --- 🔐 SISTEMA DE AUTENTICAÇÃO E SETUP 🔐 ---
def setup_authentication():
    """Gerencia o .env, pede o token e valida no Real-Debrid."""
    env_file = ".env"
    
    # 1. Verifica se o arquivo existe
    if not os.path.exists(env_file):
        console.print(Panel.fit(
            "[bold yellow]⚠️  CONFIGURAÇÃO INICIAL NECESSÁRIA[/bold yellow]\n\n"
            "Parece que é sua primeira vez aqui (ou você deletou o .env).\n"
            "Precisamos do seu [bold cyan]API Token[/bold cyan] do Real-Debrid.\n\n"
            "1. Acesse: [link=https://real-debrid.com/apitoken]https://real-debrid.com/apitoken[/link]\n"
            "2. Copie o código gigante (Token Private).\n"
            "3. Cole abaixo.",
            title="Futaba Streamer Setup", border_style="cyan"
        ))
        
        token = Prompt.ask("[bold white]Cole seu Token aqui[/bold white]").strip()
        
        if not token:
            console.print("[red]Token vazio? Assim não dá, chefinho. Tenta de novo.[/red]")
            sys.exit(1)
            
        with open(env_file, "w") as f:
            f.write(f"RD_TOKEN={token}")
        console.print("[green]Token salvo em .env com sucesso![/green]")

    # 2. Carrega o ambiente
    load_dotenv()
    token = os.getenv("RD_TOKEN")

    if not token:
        console.print("[bold red]ERRO:[/bold red] O arquivo .env existe mas o RD_TOKEN está vazio.")
        sys.exit(1)

    # 3. Valida o Token (Login Check)
    with console.status("[bold cyan]Validando credenciais...[/bold cyan]"):
        try:
            headers = {"Authorization": f"Bearer {token}"}
            # Timeout curto pq só queremos saber se conecta
            r = requests.get("https://api.real-debrid.com/rest/1.0/user", headers=headers, timeout=10)
            
            if r.status_code == 401:
                console.print(Panel(
                    "[bold red]⛔ ACESSO NEGADO[/bold red]\n\n"
                    "Seu token é inválido ou expirou.\n"
                    "Delete o arquivo [bold].env[/bold] e rode o script novamente para configurar.",
                    border_style="red"
                ))
                sys.exit(1)
            elif r.status_code != 200:
                console.print(f"[red]Erro ao conectar no RD: {r.status_code}[/red]")
                sys.exit(1)
            
            user_info = r.json()
            username = user_info.get('username', 'Usuário')
            premium_days = user_info.get('type', 'free') # premium ou free
            
            if premium_days != 'premium':
                console.print("[yellow]Aviso: Sua conta Real-Debrid não é Premium. Isso pode não funcionar.[/yellow]")
            
            console.print(f"[green]✓ Login verificado![/green] Bem-vindo de volta, [bold cyan]{username}[/bold cyan].")
            return token

        except requests.exceptions.ConnectionError:
            console.print("[red]Falha de conexão. Verifique sua internet.[/red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Erro desconhecido na autenticação: {e}[/red]")
            sys.exit(1)

# Executa o setup ANTES de iniciar a classe
check_system_dependencies()
RD_TOKEN = setup_authentication()

class AnimeStreamer:
    def __init__(self):
        # O token já foi validado lá em cima, só usamos ele
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {RD_TOKEN}"})
        
        self.scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
        )

    def search_nyaa(self, query):
        console.print(f"[cyan]🔍 Buscando por:[/cyan] [bold white]{query}[/bold white]...")
        domains = ["https://nyaa.iss.one", "https://nyaa.si"]
        
        for domain in domains:
            url = f"{domain}/?f=0&c=1_2&q={urllib.parse.quote(query)}"
            try:
                r = self.scraper.get(url)
                if "ddos-guard" in r.text.lower():
                    console.print(f"[yellow]⚠️ DDoS-Guard detectado em {domain}.[/yellow]")

                soup = BeautifulSoup(r.text, 'html.parser')
                rows = soup.select('tr.default, tr.success, tr.danger')
                
                if not rows:
                    if "0 results found" in r.text: continue 
                    continue

                results = []
                for row in rows:
                    cols = row.find_all('td')
                    if not cols: continue

                    title_links = cols[1].find_all('a')
                    if not title_links: continue
                    title = title_links[-1].text.strip()
                    
                    link_col = cols[2]
                    magnets = link_col.find_all('a', href=re.compile(r'magnet:\?'))
                    if not magnets: continue
                    magnet = magnets[0]['href']
                    
                    size = cols[3].text.strip()
                    
                    group_match = re.match(r"^\[(.*?)\]", title)
                    group = group_match.group(1) if group_match else "Unknown"

                    results.append({"title": title, "size": size, "magnet": magnet, "group": group})

                if results: return results

            except Exception as e:
                console.print(f"[red]Erro ao conectar em {domain}: {e}[/red]")
                continue
        return []

    def display_results(self, results):
        if not results:
            console.print("[yellow]Nenhum resultado encontrado.[/yellow]")
            return None

        table = Table(title="Resultados da Busca (Nyaa.si)", show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("#", style="dim", width=4)
        table.add_column("Grp", style="cyan", width=12)
        table.add_column("Título", style="white")
        table.add_column("Tam.", style="green", justify="right")

        for idx, item in enumerate(results):
            clean_title = item['title'].replace(f"[{item['group']}]", "").strip()[:70]
            table.add_row(str(idx + 1), item['group'], clean_title, item['size'])

        console.print(table)
        choice = IntPrompt.ask("Selecione (0 para sair)", choices=[str(i) for i in range(len(results) + 1)])
        
        if choice == 0: return None
        return results[choice - 1]

    def extract_videos(self, files):
        """Separa e ordena os vídeos do payload do RD."""
        video_extensions = ('.mkv', '.mp4', '.avi', '.webm')
        videos = [f for f in files if f['path'].lower().endswith(video_extensions)]
        # Ordena alfabeticamente pelo path (garante ordem E01, E02...)
        videos.sort(key=lambda x: x['path'])
        return videos

    # --- ✨ A NOVA MÁGICA: PREVISÃO DE PRÓXIMO EPISÓDIO ✨ ---
    def predict_next_query(self, current_filename, group):
        """
        Tenta adivinhar qual a busca para o próximo episódio baseada no nome do arquivo atual.
        Ex: '[Erai-raws] Frieren - 12 [1080p].mkv' -> 'Erai-raws Frieren 13'
        """
        # 1. Limpeza pesada pra evitar falsos positivos (1080p, 264, 265, 10bit)
        clean_name = current_filename.lower()
        clean_name = re.sub(r'\[.*?\]|\(.*?\)', '', clean_name) # Tira tudo entre colchetes/parenteses
        clean_name = re.sub(r'\.mkv|\.mp4', '', clean_name)      # Tira extensão
        
        # Regex Otaku: Procura padrões comuns de episódio
        # Padrão 1: " - 12 " (O mais comum em fansubs)
        # Padrão 2: " E12 " ou " Ep12 "
        # Padrão 3: " S01E12 "
        patterns = [
            r' - (\d+)\b',
            r'\bS\d+E(\d+)\b',
            r'[ _]E(\d+)\b',
            r'[ _](\d{2,4})\b' # O perigoso (numero solto), deixamos por ultimo
        ]

        episode_num = None
        for pat in patterns:
            match = re.search(pat, current_filename, re.IGNORECASE)
            if match:
                num_str = match.group(1)
                # Filtro de Sanidade: Se for 1080, 720, 264, 1920, ignora
                if num_str in ['1080', '720', '480', '264', '265', '1920']:
                    continue
                episode_num = int(num_str)
                break
        
        if episode_num is None:
            return None

        # Calcula o próximo
        next_ep = episode_num + 1
        
        # Formata com zero à esquerda se o original tinha
        # (Mas pra busca no Nyaa, numero simples costuma funcionar melhor)
        next_ep_str = f"{next_ep:02d}" 
        
        # Extrai o nome do anime (remove o grupo e tenta limpar o resto)
        # Pega o nome do arquivo original
        anime_title = current_filename
        # Remove o grupo ex: [Erai-raws]
        if group != "Unknown":
            anime_title = anime_title.replace(f"[{group}]", "").replace(group, "")
        
        # Remove tags comuns pra deixar a busca "aberta"
        anime_title = re.sub(r'\[.*?\]|\(.*?\)', '', anime_title)
        anime_title = re.sub(r'\.mkv|\.mp4', '', anime_title)
        
        # Tenta remover o número do episódio antigo do título pra não buscar "Frieren 12 13"
        # Remove " - 12" ou " 12 "
        anime_title = re.sub(fr'\b[- _]?{episode_num:02d}\b|\b[- _]?{episode_num}\b', '', anime_title)
        
        # Limpa espaços extras
        anime_title = " ".join(anime_title.split())
        
        # Monta a nova Query: Grupo + Nome Limpo + Novo Numero
        # Ex: Erai-raws Sousou no Frieren 13
        new_query = f"{group} {anime_title} {next_ep_str}"
        return new_query
    
    def prompt_episode_selection(self, videos):
        """Menu de seleção de episódios."""
        if not videos: return None

        console.print(f"\n[bold yellow]📦 BATCH: {len(videos)} episódios encontrados.[/bold yellow]")
        
        limit = 30
        table = Table(show_header=True, header_style="bold blue", box=box.SIMPLE)
        table.add_column("#", style="dim", width=4)
        table.add_column("Arquivo", style="white")
        table.add_column("Tamanho", style="green", justify="right")

        for idx, f in enumerate(videos[:limit]):
            filename = f['path'].split('/')[-1]
            size_gb = f['bytes'] / 1024 / 1024 / 1024
            table.add_row(str(idx + 1), filename, f"{size_gb:.2f} GB")
        
        if len(videos) > limit:
            table.add_row("...", f"Mais {len(videos)-limit} arquivos...", "")

        console.print(table)
        choice = IntPrompt.ask("Qual episódio iniciar?", choices=[str(i+1) for i in range(len(videos))])
        return choice - 1 # Retorna o índice (0-based)


    def process_magnet(self, magnet):
        """Retorna uma string (nova query) se o usuário quiser continuar, ou None."""
        try:
            # --- FASE 1: Adicionar e Processar ---
            console.print("[cyan]⚡ Enviando magnet pro RD...[/cyan]")
            r = self.session.post("https://api.real-debrid.com/rest/1.0/torrents/addMagnet", data={"magnet": magnet})
            if r.status_code != 201:
                console.print(f"[bold red]Erro ({r.status_code}):[/bold red] {r.json().get('error')}")
                return None

            tid = r.json()['id']

            console.print("[cyan]⏳ Lendo estrutura dos arquivos...[/cyan]")
            while True:
                r = self.session.get(f"https://api.real-debrid.com/rest/1.0/torrents/info/{tid}")
                info = r.json()
                if info['status'] == 'waiting_files_selection': break
                elif info['status'] == 'magnet_error': 
                    console.print("[red]Erro no magnet.[/red]")
                    return None
                time.sleep(1)

            # Extrai vídeos
            videos = self.extract_videos(info['files'])
            if not videos:
                console.print("[red]Nenhum vídeo encontrado.[/red]")
                return None

            # --- VERIFICA SE É BATCH OU SINGLE ---
            is_batch = len(videos) > 1

            if is_batch:
                # ==========================================
                # LÓGICA DE BATCH (Já existente)
                # ==========================================
                all_video_ids = [str(f['id']) for f in videos]
                self.session.post(f"https://api.real-debrid.com/rest/1.0/torrents/selectFiles/{tid}", data={"files": ",".join(all_video_ids)})

                current_index = self.prompt_episode_selection(videos)
                
                while True:
                    if current_index >= len(videos):
                        console.print("[green]Você terminou todos os episódios desse batch![/green]")
                        break

                    target_file = videos[current_index]
                    console.print(f"[bold green]▶️  Tocando: {target_file['path'].split('/')[-1]}[/bold green]")
                    stream_url = self.get_stream_link(tid, target_file['id'])
                    
                    if not stream_url: break
                    self.play_mpv(stream_url)

                    # Menu Pós-Episódio Batch
                    if current_index + 1 >= len(videos):
                        console.print("[yellow]Fim do batch.[/yellow]")
                        break

                    next_ep_name = videos[current_index + 1]['path'].split('/')[-1]
                    console.print(Panel(f"[bold]Episódio encerrado![/bold]\nPróximo: [cyan]{next_ep_name}[/cyan]", title="Batch Mode", border_style="purple"))
                    console.print("[dim]Opções: [bold white][N][/bold white] Próximo | [bold white][S][/bold white] Selecionar | [bold white][M][/bold white] Menu Principal[/dim]")
                    
                    action = Prompt.ask("O que fazer?", choices=["n", "s", "m"], default="n", show_choices=False)
                    if action == "n": current_index += 1
                    elif action == "s": current_index = self.prompt_episode_selection(videos)
                    elif action == "m": return None

            else:
                # ==========================================
                # LÓGICA DE SINGLE EPISODE (Nova!) 🆕
                # ==========================================
                target_file = videos[0]
                self.session.post(f"https://api.real-debrid.com/rest/1.0/torrents/selectFiles/{tid}", data={"files": target_file['id']})
                
                console.print(f"[bold green]▶️  Tocando Single: {target_file['path'].split('/')[-1]}[/bold green]")
                stream_url = self.get_stream_link(tid, target_file['id'])
                
                if stream_url:
                    self.play_mpv(stream_url)
                    
                    # --- AQUI ESTÁ O PULO DO GATO ---
                    # Tenta prever a próxima busca
                    filename = target_file['path'].split('/')[-1]
                    # Precisamos do 'group' que está lá no 'selection' do main loop, mas aqui só temos acesso local.
                    # Solução rápida: Tentar extrair do filename se não tivermos.
                    # Mas o 'main loop' passou 'magnet'. Vamos tentar adivinhar o grupo do filename.
                    group_match = re.match(r"^\[(.*?)\]", filename)
                    guessed_group = group_match.group(1) if group_match else "Unknown"
                    
                    next_query = self.predict_next_query(filename, guessed_group)
                    
                    if next_query:
                        console.print(Panel(
                            f"[bold]Episódio Único Encerrado![/bold]\n"
                            f"Sugestão de próxima busca: [bold cyan]'{next_query}'[/bold cyan]",
                            title="Single Mode", border_style="blue"
                        ))
                        console.print("[dim]Opções: [bold white][B][/bold white] Buscar Próximo | [bold white][M][/bold white] Menu Principal[/dim]")
                        
                        if Prompt.ask("Buscar próximo?", choices=["b", "m"], default="b", show_choices=False) == "b":
                            return next_query # Retorna a query pro Main Loop!
            
            return None # Volta pro menu normal

        except Exception as e:
            console.print(f"[bold red]Erro fatal:[/bold red] {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_stream_link(self, tid, file_id):
        """Lógica isolada de recuperar link com retry e mapeamento."""
        console.print("[cyan]🔗 Gerando link...[/cyan]")
        attempts = 0
        while attempts < 20:
            r = self.session.get(f"https://api.real-debrid.com/rest/1.0/torrents/info/{tid}")
            data = r.json()
            links = data['links']
            
            if data['status'] == 'downloading':
                console.print(f"[red]⚠️ Cache miss ({data.get('progress', 0)}%). RD está baixando.[/red]")
                return None
            
            # Se já tem links suficientes (idealmente todos), tenta mapear
            if len(links) > 0:
                # Mapeamento
                rd_files = data['files']
                selected_ordered = [f for f in rd_files if f['selected'] == 1]
                
                target_idx = -1
                for i, f in enumerate(selected_ordered):
                    if f['id'] == file_id:
                        target_idx = i
                        break
                
                if target_idx != -1 and target_idx < len(links):
                    # Link encontrado!
                    host_link = links[target_idx]
                    # Unrestrict
                    un = self.session.post("https://api.real-debrid.com/rest/1.0/unrestrict/link", data={"link": host_link})
                    if un.status_code == 200:
                        return un.json()['download']
            
            time.sleep(1)
            attempts += 1
        return None

    def play_mpv(self, url):
        # --force-window garante que abra rápido, --fs opcional
        subprocess.run(["mpv", url, "--force-window=immediate"])

if __name__ == "__main__":
    streamer = AnimeStreamer()
    
    # Variável pra guardar a busca automática
    next_auto_query = None

    while True:
        console.rule("[bold purple]Futaba Streamer v5.1 (Auto-Sequencer)[/bold purple]")
        
        if next_auto_query:
            console.print(f"[cyan]🔄 Busca Automática:[/cyan] {next_auto_query}")
            query = next_auto_query
            next_auto_query = None # Limpa pra não loopar infinito se falhar
        else:
            query = Prompt.ask("O que vamos assistir hoje?")
        
        if query.lower() in ['sair', 'exit', 'quit']: break
            
        results = streamer.search_nyaa(query)
        selection = streamer.display_results(results)
        
        if selection:
            console.print(f"[dim]Grupo: [bold cyan]{selection['group']}[/bold cyan][/dim]")
            
            # Agora o process_magnet pode retornar uma string (nova busca)
            next_search = streamer.process_magnet(selection['magnet'])
            
            if next_search:
                next_auto_query = next_search
                # O loop reinicia e já cai no 'if next_auto_query' lá em cima!