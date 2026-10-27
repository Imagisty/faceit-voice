use prost::Message;
use serde::Serialize;
use source2_demo::prelude::*;
use source2_demo_protobufs::{CDemoFileHeader, EDemoCommands};
use std::collections::HashMap;
use std::fs::File;
use std::io::BufReader;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
mod audio;

#[derive(Clone, Serialize)]
struct Player {
    name: String,
    steamid: String,
    user_id: u32,
    team: u8,
}

#[derive(Serialize)]
struct ScanResult {
    map: String,
    tick: u32,
    players: Vec<Player>,
}

static PLAYERS: Mutex<Option<HashMap<String, Player>>> = Mutex::new(None);
static MAP_NAME: Mutex<Option<String>> = Mutex::new(None);

#[derive(Default)]
struct PlayerCollector;

#[observer]
#[uses_entities]
impl PlayerCollector {
    #[on_entity("CCSPlayerController")]
    fn on_player_controller(&mut self, entity: &Entity) -> ObserverResult {
        let Some(name): Option<String> = try_property!(entity, "m_iszPlayerName") else {
            return Ok(());
        };
        let Some(steam_id): Option<u64> = try_property!(entity, "m_steamID") else {
            return Ok(());
        };
        let Some(team): Option<u8> = try_property!(entity, "m_iTeamNum") else {
            return Ok(());
        };
        let user_id = (entity.index() as u32).saturating_sub(1);
        if steam_id != 0 && (team == 2 || team == 3) && user_id < 64 {
            if let Ok(mut guard) = PLAYERS.lock() {
                if let Some(players) = guard.as_mut() {
                    players.insert(
                        steam_id.to_string(),
                        Player {
                            name,
                            steamid: steam_id.to_string(),
                            user_id,
                            team,
                        },
                    );
                }
            }
        }
        Ok(())
    }
}

#[derive(Default)]
struct MapCollector;

impl Observer for MapCollector {
    fn interests(&self) -> Interests {
        Interests::DEMO_MESSAGE
    }

    fn on_demo_command(
        &mut self,
        _ctx: &Context,
        msg_type: EDemoCommands,
        msg: &[u8],
    ) -> ObserverResult {
        if msg_type == EDemoCommands::DemFileHeader {
            if let Ok(header) = CDemoFileHeader::decode(msg) {
                if let Ok(mut guard) = MAP_NAME.lock() {
                    *guard = header.map_name.or(header.server_name);
                }
            }
        }
        Ok(())
    }
}

struct PreparedDemo {
    path: PathBuf,
    temporary: bool,
}

impl Drop for PreparedDemo {
    fn drop(&mut self) {
        if self.temporary {
            let _ = std::fs::remove_file(&self.path);
        }
    }
}

fn prepare_path(path: &Path) -> Result<PreparedDemo, Box<dyn std::error::Error>> {
    if !path.to_string_lossy().to_ascii_lowercase().ends_with(".zst") {
        return Ok(PreparedDemo { path: path.to_owned(), temporary: false });
    }
    let target = std::env::temp_dir().join(format!(
        "faceit_voice_{}_{}.dem",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)?
            .as_nanos()
    ));
    let mut source = zstd::stream::read::Decoder::new(File::open(path)?)?;
    let mut dest = File::create(&target)?;
    if let Err(err) = std::io::copy(&mut source, &mut dest) {
        drop(dest);
        let _ = std::fs::remove_file(&target);
        return Err(Box::new(err));
    }
    Ok(PreparedDemo { path: target, temporary: true })
}

fn scan(path: &Path) -> Result<ScanResult, Box<dyn std::error::Error>> {
    let demo = prepare_path(path)?;
    let result = std::thread::Builder::new()
        .stack_size(8 * 1024 * 1024)
        .spawn(move || -> Result<ScanResult, String> {
            *PLAYERS.lock().map_err(|e| e.to_string())? = Some(HashMap::new());
            *MAP_NAME.lock().map_err(|e| e.to_string())? = None;
            let file = File::open(&demo.path).map_err(|e| e.to_string())?;
            let mut parser = Parser::from_reader(BufReader::new(file)).map_err(|e| e.to_string())?;
            parser.register_observer::<PlayerCollector>();
            parser.register_observer::<MapCollector>();
            let mut tick = 5000;
            let _ = parser.run_to_tick(tick);
            if PLAYERS.lock().map_err(|e| e.to_string())?.as_ref().map_or(0, HashMap::len) < 10 {
                tick = 30000;
                let _ = parser.run_to_tick(tick);
            }
            let mut players: Vec<Player> = PLAYERS
                .lock()
                .map_err(|e| e.to_string())?
                .take()
                .unwrap_or_default()
                .into_values()
                .collect();
            players.sort_by_key(|p| p.user_id);
            let map = MAP_NAME.lock().map_err(|e| e.to_string())?.take().unwrap_or_default();
            Ok(ScanResult { map, tick, players })
        })?
        .join()
        .map_err(|_| "parser thread panicked")?
        .map_err(|e| format!("parse failed: {e}"))?;
    Ok(result)
}

fn main() {
    let result = (|| -> Result<(), Box<dyn std::error::Error>> {
        let args: Vec<_> = std::env::args_os().skip(1).collect();
        if args.first().is_some_and(|arg| arg == "--unpack") {
            if args.len() != 3 { return Err("usage: faceit_voice_parser --unpack INPUT OUTPUT".into()); }
            let mut reader = zstd::stream::read::Decoder::new(File::open(&args[1])?)?;
            let mut writer = std::fs::OpenOptions::new().write(true).create_new(true).open(&args[2])?;
            if let Err(error) = std::io::copy(&mut reader, &mut writer) {
                drop(writer);
                let _ = std::fs::remove_file(&args[2]);
                return Err(error.into());
            }
            return Ok(());
        }
        if args.first().is_some_and(|arg| arg == "--export") {
            if args.len() < 4 { return Err("usage: faceit_voice_parser --export DEMO DIRECTORY STEAMID...".into()); }
            let ids = args[3..].iter().map(|id| id.to_string_lossy().parse::<u64>()).collect::<Result<Vec<_>, _>>()?;
            let result = audio::export(Path::new(&args[1]), Path::new(&args[2]), ids)?;
            println!("{}", serde_json::to_string(&result)?);
            return Ok(());
        }
        let path = args.first().ok_or("usage: faceit_voice_parser DEMO")?;
        let result = scan(Path::new(&path))?;
        println!("{}", serde_json::to_string(&result)?);
        Ok(())
    })();
    if let Err(err) = result {
        eprintln!("{err}");
        std::process::exit(1);
    }
}
