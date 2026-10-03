// Research harness wrappers around attributed source slices. No retrieval or model.
use std::io::{self, Read};
#[derive(Debug)] enum Kind { Fact }
struct Memory { kind: Kind, content: String }
struct Item { memory: Memory, score: f64 }
struct Response { items: Vec<Item> }
struct Options { max_tokens: usize, template: String, header: Option<String>, footer: Option<String> }
fn unhex(s: &str) -> String {
    let bytes = (0..s.len()).step_by(2).map(|i| u8::from_str_radix(&s[i..i+2],16).unwrap()).collect();
    String::from_utf8(bytes).unwrap()
}
fn optional(s: &str) -> Option<String> { if s == "-" { None } else { Some(unhex(s)) } }
fn main() {
    let mut input=String::new(); io::stdin().read_to_string(&mut input).unwrap();
    for row in input.lines() {
        let f: Vec<&str> = row.split('\t').collect(); assert_eq!(f.len(),6);
        let max_tokens=f[1].parse().unwrap(); assert!(max_tokens>0);
        let options=Options { max_tokens, header:optional(f[2]),footer:optional(f[3]),template:unhex(f[4]) };
        let items=if f[5]=="-" {Vec::new()} else {f[5].split(',').map(|x| Item {memory:Memory {kind:Kind::Fact,content:unhex(x)},score:0.5}).collect()};
        let response=Response {items};
        let result=match f[0] {"stop"=>stop(response,options),"continue"=>continue_scan(response,options),_=>panic!("unknown method")}.unwrap();
        println!("{}",result.as_bytes().iter().map(|b|format!("{:02x}",b)).collect::<String>());
    }
}
