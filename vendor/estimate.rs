fn estimate_tokens(text: &str) -> usize {
    if text.is_empty() {
        return 0;
    }
    (text.len() as f32 / 4.0).ceil() as usize
}
