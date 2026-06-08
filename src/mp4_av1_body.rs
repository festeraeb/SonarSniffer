use std::io::{self, Write};

/// One encoded AV1 frame (a temporal unit of OBUs) plus its keyframe flag.
pub struct Av1Packet {
    pub data: Vec<u8>,
    pub is_key: bool,
}

/// Write a big-endian u32.
fn be32(v: u32) -> [u8; 4] {
    v.to_be_bytes()
}

/// A minimal ISOBMFF box writer: writes `size(u32) + type(4) + payload`.
fn write_box<W: Write>(w: &mut W, box_type: &[u8; 4], payload: &[u8]) -> io::Result<()> {
    let size = 8 + payload.len() as u32;
    w.write_all(&be32(size))?;
    w.write_all(box_type)?;
    w.write_all(payload)?;
    Ok(())
}

/// Build a box into a Vec (for nesting).
fn box_bytes(box_type: &[u8; 4], payload: &[u8]) -> Vec<u8> {
    let mut v = Vec::with_capacity(8 + payload.len());
    v.extend_from_slice(&be32(8 + payload.len() as u32));
    v.extend_from_slice(box_type);
    v.extend_from_slice(payload);
    v
}

// ── AV1 OBU parsing: extract the sequence header OBU for av1C ────────────────

/// Read an unsigned LEB128 from `data` at `pos`; returns (value, bytes_read).
fn read_leb128(data: &[u8], pos: usize) -> Option<(u64, usize)> {
    let mut value: u64 = 0;
    let mut i = 0;
    while i < 8 {
        let b = *data.get(pos + i)?;
        value |= ((b & 0x7f) as u64) << (i * 7);
        i += 1;
        if b & 0x80 == 0 {
            return Some((value, i));
        }
    }
    None
}

const OBU_SEQUENCE_HEADER: u8 = 1;

/// Walk the OBUs in a temporal unit and return the full sequence-header OBU
/// (header + size field + payload) for embedding in `av1C` configOBUs.
fn extract_seq_header_obu(tu: &[u8]) -> Option<Vec<u8>> {
    let mut pos = 0;
    while pos < tu.len() {
        let obu_start = pos;
        let header = tu[pos];
        let obu_type = (header >> 3) & 0x0f;
        let ext_flag = (header >> 2) & 0x01;
        let has_size = (header >> 1) & 0x01;
        pos += 1;
        if ext_flag == 1 {
            pos += 1; // extension header byte
        }
        let payload_len = if has_size == 1 {
            let (sz, n) = read_leb128(tu, pos)?;
            pos += n;
            sz as usize
        } else {
            tu.len() - pos
        };
        let obu_end = pos + payload_len;
        if obu_end > tu.len() {
            return None;
        }
        if obu_type == OBU_SEQUENCE_HEADER {
            return Some(tu[obu_start..obu_end].to_vec());
        }
        pos = obu_end;
    }
    None
}

// ── av1C box (AV1CodecConfigurationRecord) ───────────────────────────────────

/// Build the `av1C` box payload.
///
/// `seq_profile`, `seq_level_idx`, etc. are derived from the stream. For the
/// 8-bit 4:2:0 content we encode, we set: profile 0, monochrome 0,
/// subsampling 4:2:0 (x=1,y=1). The sequence-header OBU is appended as
/// `configOBUs` so decoders can initialize before the first sample.
fn build_av1c(seq_header_obu: &[u8], seq_level_idx: u8) -> Vec<u8> {
    let mut p = Vec::new();
    // byte 0: marker(1)=1, version(7)=1  → 0x81
    p.push(0x81);
    // byte 1: seq_profile(3)=0, seq_level_idx_0(5)
    p.push((0u8 << 5) | (seq_level_idx & 0x1f));
    // byte 2: seq_tier_0(1)=0, high_bitdepth(1)=0, twelve_bit(1)=0,
    //         monochrome(1)=0, chroma_subsampling_x(1)=1,
    //         chroma_subsampling_y(1)=1, chroma_sample_position(2)=0
    p.push(0b0000_1100);
    // byte 3: reserved(3)=0, initial_presentation_delay_present(1)=0,
    //         initial_presentation_delay_minus_one(4)=0
    p.push(0x00);
    // configOBUs: the sequence header OBU
    p.extend_from_slice(seq_header_obu);
    p
}

// ── Full-box helpers (version + flags prefix) ────────────────────────────────

fn full_box(box_type: &[u8; 4], version: u8, flags: u32, body: &[u8]) -> Vec<u8> {
    let mut payload = Vec::with_capacity(4 + body.len());
    payload.push(version);
    payload.extend_from_slice(&flags.to_be_bytes()[1..]); // 3 bytes
    payload.extend_from_slice(body);
    box_bytes(box_type, &payload)
}

/// Mux AV1 packets into an MP4 written to `w`.
///
/// `width`/`height` in pixels, `fps` frames per second, `seq_level_idx` the AV1
/// level (5 = level 3.1, safe for typical sizes; rav1e picks the real one but
/// av1C only needs a plausible value for playback).
pub fn write_mp4<W: Write>(
    w: &mut W,
    packets: &[Av1Packet],
    width: u32,
    height: u32,
    fps: u32,
    seq_level_idx: u8,
) -> io::Result<()> {
    if packets.is_empty() {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "no packets"));
    }
    let timescale = fps.max(1);
    let sample_duration = 1u32; // one tick per frame at timescale=fps
    let n = packets.len() as u32;
    let total_duration = n * sample_duration;

    // Sequence header for av1C (from the first keyframe packet).
    let seq_obu = packets
        .iter()
        .find_map(|p| extract_seq_header_obu(&p.data))
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "no AV1 sequence header OBU"))?;
    let av1c = build_av1c(&seq_obu, seq_level_idx);

    // ── ftyp ──
    let mut ftyp_payload = Vec::new();
    ftyp_payload.extend_from_slice(b"isom"); // major brand
    ftyp_payload.extend_from_slice(&be32(0)); // minor version
    for brand in [b"isom", b"iso2", b"av01", b"mp41"] {
        ftyp_payload.extend_from_slice(brand);
    }
    let ftyp = box_bytes(b"ftyp", &ftyp_payload);

    // ── Sample tables ──
    // stsz: per-sample sizes
    let mut stsz_body = Vec::new();
    stsz_body.extend_from_slice(&be32(0)); // sample_size=0 → sizes follow
    stsz_body.extend_from_slice(&be32(n)); // sample_count
    for p in packets {
        stsz_body.extend_from_slice(&be32(p.data.len() as u32));
    }
    let stsz = full_box(b"stsz", 0, 0, &stsz_body);

    // stts: all samples same duration
    let mut stts_body = Vec::new();
    stts_body.extend_from_slice(&be32(1)); // entry_count
    stts_body.extend_from_slice(&be32(n)); // sample_count
    stts_body.extend_from_slice(&be32(sample_duration));
    let stts = full_box(b"stts", 0, 0, &stts_body);

    // stsc: one chunk holding all samples
    let mut stsc_body = Vec::new();
    stsc_body.extend_from_slice(&be32(1)); // entry_count
    stsc_body.extend_from_slice(&be32(1)); // first_chunk
    stsc_body.extend_from_slice(&be32(n)); // samples_per_chunk
    stsc_body.extend_from_slice(&be32(1)); // sample_description_index
    let stsc = full_box(b"stsc", 0, 0, &stsc_body);

    // stss: sync sample table (keyframes)
    let key_indices: Vec<u32> = packets
        .iter()
        .enumerate()
        .filter(|(_, p)| p.is_key)
        .map(|(i, _)| i as u32 + 1) // 1-based
        .collect();
    let mut stss_body = Vec::new();
    stss_body.extend_from_slice(&be32(key_indices.len() as u32));
    for k in &key_indices {
        stss_body.extend_from_slice(&be32(*k));
    }
    let stss = full_box(b"stss", 0, 0, &stss_body);

    // av01 sample entry (VisualSampleEntry + av1C)
    let mut av01 = Vec::new();
    av01.extend_from_slice(&[0u8; 6]); // reserved
    av01.extend_from_slice(&1u16.to_be_bytes()); // data_reference_index
    av01.extend_from_slice(&[0u8; 16]); // pre-defined + reserved + predefined
    av01.extend_from_slice(&(width as u16).to_be_bytes());
    av01.extend_from_slice(&(height as u16).to_be_bytes());
    av01.extend_from_slice(&0x0048_0000u32.to_be_bytes()); // horiz res 72dpi
    av01.extend_from_slice(&0x0048_0000u32.to_be_bytes()); // vert res 72dpi
    av01.extend_from_slice(&be32(0)); // reserved
    av01.extend_from_slice(&1u16.to_be_bytes()); // frame_count
    av01.extend_from_slice(&[0u8; 32]); // compressorname
    av01.extend_from_slice(&0x0018u16.to_be_bytes()); // depth 24
    av01.extend_from_slice(&0xffffu16.to_be_bytes()); // pre-defined -1
    av01.extend_from_slice(&box_bytes(b"av1C", &av1c));
    let av01_entry = box_bytes(b"av01", &av01);

    // stsd
    let mut stsd_body = Vec::new();
    stsd_body.extend_from_slice(&be32(1)); // entry_count
    stsd_body.extend_from_slice(&av01_entry);
    let stsd = full_box(b"stsd", 0, 0, &stsd_body);

    // mdat starts after ftyp + moov. We must compute chunk offset (stco) which
    // points at the first sample's byte offset in the file. moov size depends on
    // stco itself, so we build moov with a placeholder, then patch the offset.
    // Simpler: place mdat AFTER moov and compute offset once moov is sized.

    // Build stbl with a placeholder stco (single chunk offset).
    let make_moov = |chunk_offset: u32| -> Vec<u8> {
        let mut stco_body = Vec::new();
        stco_body.extend_from_slice(&be32(1)); // entry_count
        stco_body.extend_from_slice(&be32(chunk_offset));
        let stco = full_box(b"stco", 0, 0, &stco_body);

        let mut stbl = Vec::new();
        stbl.extend_from_slice(&stsd);
        stbl.extend_from_slice(&stts);
        stbl.extend_from_slice(&stss);
        stbl.extend_from_slice(&stsc);
        stbl.extend_from_slice(&stsz);
        stbl.extend_from_slice(&stco);
        let stbl = box_bytes(b"stbl", &stbl);

        // dinf → dref → url
        let url = full_box(b"url ", 0, 1, &[]); // flags=1 → self-contained
        let mut dref_body = Vec::new();
        dref_body.extend_from_slice(&be32(1));
        dref_body.extend_from_slice(&url);
        let dref = full_box(b"dref", 0, 0, &dref_body);
        let dinf = box_bytes(b"dinf", &dref);

        // vmhd
        let vmhd = full_box(b"vmhd", 0, 1, &[0, 0, 0, 0, 0, 0, 0, 0]);

        let mut minf = Vec::new();
        minf.extend_from_slice(&vmhd);
        minf.extend_from_slice(&dinf);
        minf.extend_from_slice(&stbl);
        let minf = box_bytes(b"minf", &minf);

        // hdlr (vide)
        let mut hdlr_body = Vec::new();
        hdlr_body.extend_from_slice(&be32(0)); // pre_defined
        hdlr_body.extend_from_slice(b"vide");
        hdlr_body.extend_from_slice(&[0u8; 12]); // reserved
        hdlr_body.extend_from_slice(b"SonarSniffer\0");
        let hdlr = full_box(b"hdlr", 0, 0, &hdlr_body);

        // mdhd
        let mut mdhd_body = Vec::new();
        mdhd_body.extend_from_slice(&be32(0)); // creation
        mdhd_body.extend_from_slice(&be32(0)); // modification
        mdhd_body.extend_from_slice(&be32(timescale));
        mdhd_body.extend_from_slice(&be32(total_duration));
        mdhd_body.extend_from_slice(&0x55c4u16.to_be_bytes()); // language 'und'
        mdhd_body.extend_from_slice(&0u16.to_be_bytes()); // pre_defined
        let mdhd = full_box(b"mdhd", 0, 0, &mdhd_body);

        let mut mdia = Vec::new();
        mdia.extend_from_slice(&mdhd);
        mdia.extend_from_slice(&hdlr);
        mdia.extend_from_slice(&minf);
        let mdia = box_bytes(b"mdia", &mdia);

        // tkhd (flags=3 → enabled+in movie)
        let mut tkhd_body = Vec::new();
        tkhd_body.extend_from_slice(&be32(0)); // creation
        tkhd_body.extend_from_slice(&be32(0)); // modification
        tkhd_body.extend_from_slice(&be32(1)); // track_id
        tkhd_body.extend_from_slice(&be32(0)); // reserved
        tkhd_body.extend_from_slice(&be32(total_duration));
        tkhd_body.extend_from_slice(&[0u8; 8]); // reserved
        tkhd_body.extend_from_slice(&0u16.to_be_bytes()); // layer
        tkhd_body.extend_from_slice(&0u16.to_be_bytes()); // alternate_group
        tkhd_body.extend_from_slice(&0u16.to_be_bytes()); // volume
        tkhd_body.extend_from_slice(&0u16.to_be_bytes()); // reserved
        // unity matrix
        for v in [0x00010000u32, 0, 0, 0, 0x00010000, 0, 0, 0, 0x40000000] {
            tkhd_body.extend_from_slice(&be32(v));
        }
        tkhd_body.extend_from_slice(&(width << 16).to_be_bytes()); // width 16.16
        tkhd_body.extend_from_slice(&(height << 16).to_be_bytes()); // height 16.16
        let tkhd = full_box(b"tkhd", 0, 3, &tkhd_body);

        let mut trak = Vec::new();
        trak.extend_from_slice(&tkhd);
        trak.extend_from_slice(&mdia);
        let trak = box_bytes(b"trak", &trak);

        // mvhd
        let mut mvhd_body = Vec::new();
        mvhd_body.extend_from_slice(&be32(0)); // creation
        mvhd_body.extend_from_slice(&be32(0)); // modification
        mvhd_body.extend_from_slice(&be32(timescale));
        mvhd_body.extend_from_slice(&be32(total_duration));
        mvhd_body.extend_from_slice(&0x00010000u32.to_be_bytes()); // rate 1.0
        mvhd_body.extend_from_slice(&0x0100u16.to_be_bytes()); // volume 1.0
        mvhd_body.extend_from_slice(&0u16.to_be_bytes()); // reserved
        mvhd_body.extend_from_slice(&[0u8; 8]); // reserved
        for v in [0x00010000u32, 0, 0, 0, 0x00010000, 0, 0, 0, 0x40000000] {
            mvhd_body.extend_from_slice(&be32(v));
        }
        mvhd_body.extend_from_slice(&[0u8; 24]); // pre_defined
        mvhd_body.extend_from_slice(&be32(2)); // next_track_id
        let mvhd = full_box(b"mvhd", 0, 0, &mvhd_body);

        let mut moov = Vec::new();
        moov.extend_from_slice(&mvhd);
        moov.extend_from_slice(&trak);
        box_bytes(b"moov", &moov)
    };

    // First pass: build moov with offset=0 to learn its size.
    let moov_probe = make_moov(0);
    // mdat payload starts 8 bytes into the mdat box (after size+type).
    let chunk_offset = (ftyp.len() + moov_probe.len() + 8) as u32;
    let moov = make_moov(chunk_offset);

    // mdat
    let mdat_payload_len: usize = packets.iter().map(|p| p.data.len()).sum();
    w.write_all(&ftyp)?;
    w.write_all(&moov)?;
    // mdat header
    w.write_all(&be32(8 + mdat_payload_len as u32))?;
    w.write_all(b"mdat")?;
    for p in packets {
        w.write_all(&p.data)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn leb128_roundtrip() {
        // Single-byte and multi-byte.
        let data = [0x05];
        assert_eq!(read_leb128(&data, 0), Some((5, 1)));
        let data = [0x80, 0x01]; // 128
        assert_eq!(read_leb128(&data, 0), Some((128, 2)));
    }

    #[test]
    fn extract_seq_header_from_tu() {
        // OBU header: type=1 (seq header), has_size=1 → 0b0000_1010 = 0x0a
        // size = 3, payload = [0xaa,0xbb,0xcc]
        let tu = [0x0a, 0x03, 0xaa, 0xbb, 0xcc];
        let obu = extract_seq_header_obu(&tu).unwrap();
        assert_eq!(obu, vec![0x0a, 0x03, 0xaa, 0xbb, 0xcc]);
    }

    #[test]
    fn mux_produces_valid_structure() {
        // Fake packets with a seq-header OBU in the first.
        let key = Av1Packet {
            data: vec![0x0a, 0x02, 0x11, 0x22], // seq header OBU type=1
            is_key: true,
        };
        let inter = Av1Packet {
            data: vec![0x32, 0x02, 0x33, 0x44], // frame OBU type=6
            is_key: false,
        };
        let mut out = Vec::new();
        write_mp4(&mut out, &[key, inter], 64, 48, 10, 5).unwrap();
        // Starts with ftyp box.
        assert_eq!(&out[4..8], b"ftyp");
        // Contains moov and mdat.
        let s = out.windows(4).any(|w| w == b"moov");
        let m = out.windows(4).any(|w| w == b"mdat");
        let a = out.windows(4).any(|w| w == b"av1C");
        assert!(s && m && a, "moov/mdat/av1C present");
    }
}
