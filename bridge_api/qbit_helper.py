import sqlite3
import qbittorrentapi
import time
import subprocess
import os
import shutil
import re

def extract_with_progress(fpath: str, extract_to: str, progress_callback=None):
    # Run 7z in a subprocess and capture stdout in real time
    process = subprocess.Popen(
        ["7z", "x", fpath, f"-o{extract_to}", "-y", "-bsp1"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            match = re.search(r'(\d+)%', line)
            if match:
                percent = int(match.group(1))
                if progress_callback:
                    progress_callback(percent)
                    
    process.communicate() # wait for process to finish
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, process.args)

def download_via_qbittorrent(filename: str, folder_path: str, progress_callback, full_path: str = None):
    db_path = "/roms/hashes.db"
    if not os.path.exists(db_path):
        raise Exception("Base de datos hashes.db no encontrada en /roms")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    if full_path:
        cursor.execute("SELECT magnet FROM files WHERE full_path = ? AND full_path NOT LIKE '%Disc Keys%'", (full_path,))
    else:
        cursor.execute("SELECT magnet FROM files WHERE file_name = ? AND full_path NOT LIKE '%Disc Keys%'", (filename,))
    row = cursor.fetchone()
    conn.close()
    
    if not row or not row[0]:
        raise Exception("Magnet link no encontrado en la base de datos de Minerva")
    
    magnet_link = row[0]
    
    qbt_client = qbittorrentapi.Client(host='qbittorrent:8080', REQUESTS_ARGS={'timeout': 60})
    try:
        qbt_client.auth_log_in()
    except Exception as e:
        raise Exception(f"Fallo al conectar con qBittorrent: {e}")
        
    # Agregamos el torrent activo para que descargue los metadatos del magnet
    try:
        qbt_client.torrents_add(urls=magnet_link, save_path=folder_path, is_paused=False)
    except Exception as e:
        if "Conflict" not in str(e) and "409" not in str(e):
            raise e
            
    time.sleep(3)
    
    # Encontrar el torrent recién añadido
    torrents = qbt_client.torrents_info()
    my_torrent = None
    for t in torrents:
        if t.magnet_uri == magnet_link or t.save_path == folder_path:
            my_torrent = t
            break
            
    if not my_torrent:
        my_torrent = torrents[-1] if torrents else None
        
    if not my_torrent:
        raise Exception("El torrent no se añadió a qBittorrent")
        
    torrent_hash = my_torrent.hash
    progress_callback(0, status="Esperando metadatos", torrent_hash=torrent_hash)
    
    # Inyectar trackers públicos estables para acelerar la búsqueda de pares y estabilizar la velocidad
    public_trackers = [
        'udp://tracker.opentrackr.org:1337/announce',
        'udp://open.demonii.com:1337/announce',
        'udp://open.stealth.si:80/announce',
        'udp://tracker.torrent.eu.org:451/announce',
        'udp://tracker.srv00.com:6969/announce',
        'udp://tracker.qu.ax:6969/announce'
    ]
    try:
        qbt_client.torrents_add_trackers(torrent_hash=torrent_hash, urls=public_trackers)
        print("Trackers públicos inyectados para estabilización de velocidad.")
    except Exception as e:
        print(f"Aviso: No se pudieron inyectar los trackers adicionales: {e}")
    
    # Asegurar que no esté pausado (por si hubo conflictos previos)
    qbt_client.torrents_resume(torrent_hashes=torrent_hash)
    
    # Esperar a que se descarguen los metadatos (necesario para magnet links)
    print("Esperando metadatos del torrent...")
    while True:
        try:
            t_info = qbt_client.torrents_info(torrent_hashes=torrent_hash)[0]
            if t_info.state == 'error':
                raise Exception("El torrent tiene un estado de error en qBittorrent (posible problema de permisos o de red).")
            if t_info.size > 0 and t_info.state != 'metaDL':
                break
        except Exception as e:
            err_str = str(e).lower()
            if "timeout" in err_str or "connection" in err_str or "max retries" in err_str or "readtimeout" in err_str:
                print(f"Aviso: Error temporal al obtener metadatos: {e}. Reintentando...")
                time.sleep(5)
                continue
            else:
                raise e
        time.sleep(2)
        
    # Seleccionar solo el archivo que queremos
    files = []
    while True:
        try:
            files = qbt_client.torrents_files(torrent_hash=torrent_hash)
            break
        except Exception as e:
            err_str = str(e).lower()
            if "timeout" in err_str or "connection" in err_str or "max retries" in err_str or "readtimeout" in err_str:
                print(f"Aviso: Error temporal al obtener lista de archivos: {e}. Reintentando...")
                time.sleep(5)
                continue
            else:
                raise e

    file_id_to_download = -1
    for f in files:
        if filename.replace(".zip", "") in f.name or filename in f.name:
            file_id_to_download = f.id
            break
            
    if file_id_to_download == -1:
        # Borrar el torrent si no encontramos el archivo
        try:
            qbt_client.torrents_delete(delete_files=True, torrent_hashes=torrent_hash)
        except Exception:
            pass
        raise Exception(f"El archivo {filename} no se encontró dentro del torrent.")
        
    # Deseleccionar todos y seleccionar solo el archivo deseado
    while True:
        try:
            all_file_ids = [f.id for f in files]
            qbt_client.torrents_file_priority(torrent_hash=torrent_hash, file_ids=all_file_ids, priority=0)
            qbt_client.torrents_file_priority(torrent_hash=torrent_hash, file_ids=file_id_to_download, priority=1)
            break
        except Exception as e:
            err_str = str(e).lower()
            if "timeout" in err_str or "connection" in err_str or "max retries" in err_str or "readtimeout" in err_str:
                print(f"Aviso: Error temporal al configurar prioridades: {e}. Reintentando...")
                time.sleep(5)
                continue
            else:
                raise e
    
    # Reanudar la descarga
    while True:
        try:
            qbt_client.torrents_resume(torrent_hashes=torrent_hash)
            break
        except Exception as e:
            err_str = str(e).lower()
            if "timeout" in err_str or "connection" in err_str or "max retries" in err_str or "readtimeout" in err_str:
                print(f"Aviso: Error temporal al reanudar: {e}. Reintentando...")
                time.sleep(5)
                continue
            else:
                raise e
    
    print(f"Descargando {filename} vía qBittorrent...")
    
    while True:
        try:
            t_info = qbt_client.torrents_info(torrent_hashes=torrent_hash)[0]
            progress = int(t_info.progress * 100)
            status = "Pausado" if "paused" in t_info.state.lower() else "Descargando"
            progress_callback(
                progress,
                status=status,
                dlspeed=getattr(t_info, 'dlspeed', 0),
                eta=getattr(t_info, 'eta', -1)
            )
            
            if t_info.state == 'error':
                raise Exception("El torrent entró en estado de error durante la descarga.")
                
            if t_info.state_enum.is_complete or progress >= 100:
                break
        except Exception as e:
            err_str = str(e).lower()
            if "timeout" in err_str or "connection" in err_str or "max retries" in err_str or "readtimeout" in err_str:
                print(f"Aviso: Error temporal de conexión en descarga activa de {filename}: {e}. Reintentando...")
                time.sleep(5)
                continue
            else:
                raise e
        time.sleep(3)
        
    progress_callback(100, status="Extrayendo")
    
    # Obtener la ruta del archivo específico descargado
    downloaded_file = None
    while True:
        try:
            downloaded_file = next(f for f in qbt_client.torrents_files(torrent_hash=torrent_hash) if f.id == file_id_to_download)
            break
        except Exception as e:
            err_str = str(e).lower()
            if "timeout" in err_str or "connection" in err_str or "max retries" in err_str or "readtimeout" in err_str:
                print(f"Aviso: Error temporal al obtener archivo completado: {e}. Reintentando...")
                time.sleep(5)
                continue
            else:
                raise e

    real_path = os.path.join(folder_path, downloaded_file.name)
    
    if os.path.exists(real_path):
        if real_path.endswith('.zip') or real_path.endswith('.7z'):
            print(f"Extrayendo {real_path} con progreso...")
            def ext_cb(pct):
                progress_callback(pct, status="Extrayendo")
            extract_with_progress(real_path, folder_path, ext_cb)
            
    # Limpiar el torrent y sus archivos en qBittorrent
    try:
        qbt_client.torrents_delete(delete_files=True, torrent_hashes=torrent_hash)
    except Exception as e:
        print(f"Error al eliminar torrent de qBittorrent: {e}")
        
    # Limpiar la estructura de directorios vacíos remanentes (ej. Minerva_Myrient/...)
    parts = downloaded_file.name.split('/')
    if len(parts) > 1:
        top_dir = os.path.join(folder_path, parts[0])
        if os.path.exists(top_dir):
            try:
                shutil.rmtree(top_dir)
                print(f"Limpieza de directorio temporal completada: {top_dir}")
            except Exception as e:
                print(f"No se pudo eliminar el directorio temporal del torrent: {e}")
