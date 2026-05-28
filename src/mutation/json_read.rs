pub fn path_to_string(path: &[String]) -> String {
    if path.is_empty() {
        return "<root>".to_string();
    }

    path.join(".")
}
