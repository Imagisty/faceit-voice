use serde::Serialize;
use source2_demo::prelude::*;
use source2_demo_protobufs::{CSvcMsgVoiceData, VoiceDataFormatT};
use std::collections::BTreeMap;
use std::fs::{File, OpenOptions};
use std::io::{BufReader, Write};
use std::path::Path;

#[derive(Default)]
struct VoiceCollector {
    tracks: BTreeMap<u64, Vec<Vec<u8>>>,
    unsupported: usize,
}

#[observer]
impl VoiceCollector {
    #[on_message]
    fn voice(&mut self, message: &CSvcMsgVoiceData) -> ObserverResult {
        let Some(packets) = self.tracks.get_mut(&message.xuid()) else { return Ok(()); };
        if let Some(audio) = &message.audio {
            if audio.voice_data().is_empty() { return Ok(()); }
            if audio.format() != VoiceDataFormatT::VoicedataFormatOpus {
                self.unsupported += 1;
                return Ok(());
            }
            packets.push(audio.voice_data().to_vec());
        }
        Ok(())
    }
}

#[derive(Serialize)]
pub struct Track {
    steamid: String,
    file: String,
    packets: usize,
    seconds: f64,
}

#[derive(Serialize)]
pub struct ExportResult {
    tracks: Vec<Track>,
    missing: Vec<String>,
}

fn samples(packet: &[u8]) -> Result<u64, String> {
    let toc = *packet.first().ok_or("Empty Opus packet")?;
    let config = toc >> 3;
    let per_frame = if config >= 16 { 120 << (config & 3) }
        else if config >= 12 { 480 << (config & 1) }
        else if config & 3 == 3 { 2880 }
        else { 480 << (config & 3) };
    let frames = match toc & 3 {
        0 => 1,
        1 | 2 => 2,
        _ => u64::from(*packet.get(1).ok_or("Truncated Opus packet")? & 0x3f),
    };
    let total = per_frame * frames;
    if total == 0 || total > 5760 { return Err("Invalid Opus packet duration".into()); }
    Ok(total)
}

fn page(payload: &[u8], serial: u32, sequence: u32, granule: u64, flags: u8) -> Result<Vec<u8>, String> {
    let segments = payload.len() / 255 + 1;
    if segments > 255 { return Err("Opus packet is too large".into()); }
    let mut bytes = Vec::with_capacity(27 + segments + payload.len());
    bytes.extend_from_slice(b"OggS");
    bytes.extend_from_slice(&[0, flags]);
    bytes.extend_from_slice(&granule.to_le_bytes());
    bytes.extend_from_slice(&serial.to_le_bytes());
    bytes.extend_from_slice(&sequence.to_le_bytes());
    bytes.extend_from_slice(&0u32.to_le_bytes());
    bytes.push(segments as u8);
    bytes.extend(std::iter::repeat_n(255u8, segments - 1));
    bytes.push((payload.len() % 255) as u8);
    bytes.extend_from_slice(payload);
    let mut crc = 0u32;
    for byte in &bytes {
        crc ^= u32::from(*byte) << 24;
        for _ in 0..8 {
            crc = (crc << 1) ^ if crc & 0x8000_0000 != 0 { 0x04c1_1db7 } else { 0 };
        }
    }
    bytes[22..26].copy_from_slice(&crc.to_le_bytes());
    Ok(bytes)
}

fn write_track(path: &Path, id: u64, packets: &[Vec<u8>]) -> Result<f64, String> {
    let mut bytes = Vec::new();
    // Mono Opus, 48 kHz, no additional encoder delay introduced by this remux.
    let mut head = b"OpusHead".to_vec();
    head.extend_from_slice(&[1, 1]);
    head.extend_from_slice(&0u16.to_le_bytes());
    head.extend_from_slice(&48000u32.to_le_bytes());
    head.extend_from_slice(&[0, 0, 0]);
    let vendor = b"FACEIT Voice";
    let mut tags = b"OpusTags".to_vec();
    tags.extend_from_slice(&(vendor.len() as u32).to_le_bytes());
    tags.extend_from_slice(vendor);
    tags.extend_from_slice(&0u32.to_le_bytes());
    bytes.extend(page(&head, id as u32, 0, 0, 2)?);
    bytes.extend(page(&tags, id as u32, 1, 0, 0)?);
    let mut granule = 0;
    for (i, packet) in packets.iter().enumerate() {
        granule += samples(packet)?;
        bytes.extend(page(packet, id as u32, i as u32 + 2, granule,
                          if i + 1 == packets.len() { 4 } else { 0 })?);
    }
    let mut file = OpenOptions::new().write(true).create_new(true).open(path).map_err(|e| e.to_string())?;
    if let Err(error) = file.write_all(&bytes) {
        drop(file);
        let _ = std::fs::remove_file(path);
        return Err(error.to_string());
    }
    Ok(granule as f64 / 48000.0)
}

pub fn export(path: &Path, output: &Path, ids: Vec<u64>) -> Result<ExportResult, String> {
    let demo = super::prepare_path(path).map_err(|e| e.to_string())?;
    let output = output.to_owned();
    std::thread::Builder::new().stack_size(8 * 1024 * 1024).spawn(move || {
        let input = BufReader::new(File::open(&demo.path).map_err(|e| e.to_string())?);
        let mut parser = Parser::from_reader(input).map_err(|e| e.to_string())?;
        let observer = parser.register_observer::<VoiceCollector>();
        for id in ids { observer.borrow_mut().tracks.insert(id, Vec::new()); }
        parser.run_to_end().map_err(|e| e.to_string())?;
        let collector = observer.borrow();
        if collector.unsupported > 0 {
            return Err("This demo contains a voice codec other than Opus".to_string());
        }
        if collector.tracks.values().all(Vec::is_empty) {
            return Err("No voice recordings found for the selected players".to_string());
        }
        let mut tracks = Vec::new();
        let mut missing = Vec::new();
        let mut created = Vec::new();
        for (id, packets) in &collector.tracks {
            if packets.is_empty() { missing.push(id.to_string()); continue; }
            let path = output.join(format!("{id}.opus"));
            match write_track(&path, *id, packets) {
                Ok(seconds) => {
                    created.push(path.clone());
                    tracks.push(Track { steamid: id.to_string(), file: path.to_string_lossy().into_owned(), packets: packets.len(), seconds });
                }
                Err(error) => {
                    for path in created { let _ = std::fs::remove_file(path); }
                    return Err(error);
                }
            }
        }
        Ok(ExportResult { tracks, missing })
    }).map_err(|e| e.to_string())?.join().map_err(|_| "Audio parser thread panicked".to_string())?
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn opus_duration_and_invalid_packet() {
        assert_eq!(samples(&[0xf8]).unwrap(), 960);
        assert_eq!(samples(&[0xf9]).unwrap(), 1920);
        assert!(samples(&[]).is_err());
        assert!(samples(&[0xff]).is_err());
        assert!(samples(&[0xff, 63]).is_err());
    }

    #[test]
    fn exact_255_byte_packet_has_terminating_segment() {
        let p = page(&vec![0; 255], 7, 2, 960, 4).unwrap();
        assert_eq!(p[26], 2);
        assert_eq!(&p[27..29], &[255, 0]);
        assert_eq!(p.len(), 284);
    }
}
