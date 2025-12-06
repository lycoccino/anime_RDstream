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
        try:
            # --- FASE 1: Adicionar e Processar ---
            console.print("[cyan]⚡ Enviando magnet pro RD...[/cyan]")
            r = self.session.post("https://api.real-debrid.com/rest/1.0/torrents/addMagnet", data={"magnet": magnet})
            if r.status_code != 201:
                console.print(f"[bold red]Erro ({r.status_code}):[/bold red] {r.json().get('error')}")
                return

            tid = r.json()['id']

            console.print("[cyan]⏳ Lendo estrutura dos arquivos...[/cyan]")
            while True:
                r = self.session.get(f"https://api.real-debrid.com/rest/1.0/torrents/info/{tid}")
                info = r.json()
                if info['status'] == 'waiting_files_selection': break
                elif info['status'] == 'magnet_error': 
                    console.print("[red]Erro no magnet.[/red]")
                    return
                time.sleep(1)

            # Extrai vídeos ordenados
            videos = self.extract_videos(info['files'])
            if not videos:
                console.print("[red]Nenhum vídeo encontrado.[/red]")
                return

            # Se for batch, seleciona TUDO pra garantir cache. Se for single, seleciona o único.
            all_video_ids = [str(f['id']) for f in videos]
            self.session.post(f"https://api.real-debrid.com/rest/1.0/torrents/selectFiles/{tid}", data={"files": ",".join(all_video_ids)})

            # Seleção inicial do usuário
            current_index = 0
            if len(videos) > 1:
                current_index = self.prompt_episode_selection(videos)
            
            # --- FASE 2: Loop de Binge Watching ---
            while True:
                if current_index >= len(videos):
                    console.print("[green]Você terminou todos os episódios desse batch![/green]")
                    break

                target_file = videos[current_index]
                console.print(f"[bold green]▶️  Tocando: {target_file['path'].split('/')[-1]}[/bold green]")

                # Busca o Link (Com Mapeamento)
                stream_url = self.get_stream_link(tid, target_file['id'])
                
                if not stream_url:
                    console.print("[red]Falha ao pegar link. Abortando sessão.[/red]")
                    break

                # TOCA O VÍDEO (Bloqueia o script até fechar o MPV)
                self.play_mpv(stream_url)

                # --- FASE 3: Menu Pós-Episódio ---
                # Se for o último, avisa e sai
                if current_index + 1 >= len(videos):
                    console.print("[yellow]Fim do batch.[/yellow]")
                    break

                # Menu interativo
                next_ep_name = videos[current_index + 1]['path'].split('/')[-1]
                
                console.print(Panel(
                    f"[bold]Episódio encerrado![/bold]\n"
                    f"Próximo: [cyan]{next_ep_name}[/cyan]",
                    title="Binge Mode", border_style="purple"
                ))
                
                # A lenda aparece ANTES de pedir o input agora (Duh!)
                console.print("[dim]Opções: [bold white][N][/bold white] Próximo | [bold white][S][/bold white] Selecionar | [bold white][M][/bold white] Menu Principal[/dim]")
                
                action = Prompt.ask(
                    "O que fazer?", 
                    choices=["n", "s", "m"], 
                    default="n",
                    show_choices=False
                )

                if action == "n":
                    current_index += 1
                elif action == "s":
                    new_choice = self.prompt_episode_selection(videos)
                    current_index = new_choice
                elif action == "m":
                    break

        except Exception as e:
            console.print(f"[bold red]Erro fatal:[/bold red] {e}")
            import traceback
            traceback.print_exc()

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
    
    while True:
        console.rule("[bold purple]Futaba Streamer v5.0 (Binge Mode)[/bold purple]")
        query = Prompt.ask("O que vamos assistir hoje?")
        
        if query.lower() in ['sair', 'exit', 'quit']: break
            
        results = streamer.search_nyaa(query)
        selection = streamer.display_results(results)
        
        if selection:
            console.print(f"[dim]Grupo: [bold cyan]{selection['group']}[/bold cyan][/dim]")
            # O process_magnet agora controla o loop de episódios sozinho
            streamer.process_magnet(selection['magnet'])