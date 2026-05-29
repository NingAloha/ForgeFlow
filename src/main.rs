#![allow(dead_code)]
#![allow(unused_imports)]

mod llm;
mod runtime;
mod sieves;

fn main() {
    use std::io::{self, Read};

    let mut raw_input = String::new();
    if let Err(err) = io::stdin().read_to_string(&mut raw_input) {
        eprintln!("failed to read stdin: {err}");
        std::process::exit(1);
    }

    match sieves::requirements::capture::capture_domain(raw_input.trim_end()) {
        Ok(value) => match serde_json::to_string_pretty(&value) {
            Ok(text) => println!("{text}"),
            Err(err) => {
                eprintln!("failed to serialize output JSON: {err}");
                std::process::exit(1);
            }
        },
        Err(err) => {
            eprintln!("{err}");
            std::process::exit(1);
        }
    }
}
