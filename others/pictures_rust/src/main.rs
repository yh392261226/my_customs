use std::env;
use std::fs::{self, File};
use std::io::{self, Write, Read};
use rand::Rng;
use log::{error, info};
use env_logger;

struct Pic {
    filedir: String,
    start: usize,
    ext: String,
    action: String,
    rand_num: usize,
    currentpage: usize,
    currentpagefile: String,
    currentnamefile: String,
    total: usize,
    filelists: Vec<String>,
}

impl Pic {
    fn new() -> Self {
        let myruntime_path = get_my_runtime_path();
        let base_dir = read_runtime_file(&myruntime_path);
        let filedir = format!("{}/pictures", base_dir); // 添加 /pictures 到路径
        let currentpagefile = format!("{}/tools/current_picture", base_dir);
        let currentnamefile = format!("{}/tools/current_picturename", base_dir);

        let mut pic = Self {
            filedir: filedir.clone(),
            start: 0,
            ext: "jpg".to_string(),
            action: "".to_string(),
            rand_num: 0,
            currentpage: 0,
            currentpagefile,
            currentnamefile,
            total: 0,
            filelists: Vec::new(),
        };
        info!("File directory: {}", pic.filedir);
        pic.get_file_lists();
        pic.get_current_page_from_file();
        pic
    }

    fn get_file_lists(&mut self) {
        info!("Scanning directory: {}", self.filedir);
        if let Ok(entries) = fs::read_dir(&self.filedir) {
            for entry in entries.flatten() {
                if let Ok(file_type) = entry.file_type() {
                    if file_type.is_file() {
                        if let Some(ext) = entry.path().extension() {
                            if let Some(ext_str) = ext.to_str() {
                                if ext_str == self.ext {
                                    if let Ok(path) = entry.path().into_os_string().into_string() {
                                        self.filelists.push(path);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        } else {
            error!("Failed to read directory: {}", self.filedir);
        }
        self.total = self.filelists.len();
        info!("Total files found: {}", self.total);
    }

    fn get_rand_num(&mut self) {
        if self.total == 0 {
            error!("No files found in the directory");
        }
        let mut rng = rand::thread_rng();
        self.rand_num = rng.gen_range(self.start..self.total);
    }

    fn get_pre_page(&self) -> usize {
        if self.currentpage <= 1 {
            self.total
        } else {
            self.currentpage - 1
        }
    }

    fn get_next_page(&self) -> usize {
        if self.currentpage >= self.total {
            1
        } else {
            self.currentpage + 1
        }
    }

    fn set_current_page_to_file(&self) {
        if let Ok(mut file) = File::create(&self.currentpagefile) {
            file.write_all(self.currentpage.to_string().as_bytes()).unwrap();
        }
        if let Some(file_path) = self.filelists.get(self.currentpage - 1) {
            if let Ok(mut file) = File::create(&self.currentnamefile) {
                file.write_all(file_path.as_bytes()).unwrap();
            }
        }
    }

    fn get_current_page_from_file(&mut self) {
        if let Ok(mut file) = File::open(&self.currentpagefile) {
            let mut contents = String::new();
            file.read_to_string(&mut contents).unwrap();
            self.currentpage = contents.parse().unwrap_or(1);
        } else {
            self.currentpage = 1;
        }
    }

    fn get_current_file_from_name_file(&self) -> Option<String> {
        if let Ok(mut file) = File::open(&self.currentnamefile) {
            let mut contents = String::new();
            file.read_to_string(&mut contents).unwrap();
            info!("Current file from name file: {}", contents.trim());
            Some(contents.trim().to_string())
        } else {
            error!("Failed to read current name file: {}", self.currentnamefile);
            None
        }
    }

    fn run(&mut self) -> io::Result<String> {
        info!("Total files: {}", self.total);
        info!("Current page: {}", self.currentpage);

        match self.action.as_str() {
            "pre" => {
                if let Some(current_file) = self.get_current_file_from_name_file() {
                    if let Some(index) = self.filelists.iter().position(|x| x == &current_file) {
                        self.currentpage = index + 1;
                        self.currentpage = self.get_pre_page();
                        self.set_current_page_to_file();
                        if let Some(file) = self.filelists.get(self.currentpage - 1) {
                            return Ok(file.clone());
                        }
                    }
                }
            }
            "next" => {
                if let Some(current_file) = self.get_current_file_from_name_file() {
                    if let Some(index) = self.filelists.iter().position(|x| x == &current_file) {
                        self.currentpage = index + 1;
                        self.currentpage = self.get_next_page();
                        self.set_current_page_to_file();
                        if let Some(file) = self.filelists.get(self.currentpage - 1) {
                            return Ok(file.clone());
                        }
                    }
                }
            }
            "rand" => {
                self.get_rand_num();
                self.currentpage = self.rand_num;
                self.set_current_page_to_file();
                if let Some(file) = self.filelists.get(self.currentpage) {
                    return Ok(file.clone());
                }
            }
            _ => {
                if let Some(file) = self.filelists.get(0) {
                    return Ok(file.clone());
                }
            }
        }
        Err(io::Error::new(io::ErrorKind::NotFound, "No file found"))
    }
}

fn get_my_runtime_path() -> String {
    let home = env::var("HOME").unwrap_or_else(|_| "".to_string());
    format!("{}/.myruntime", home)
}

fn read_runtime_file(path: &str) -> String {
    if let Ok(mut file) = File::open(path) {
        let mut contents = String::new();
        if file.read_to_string(&mut contents).is_ok() {
            return contents.trim().to_string();
        }
    }
    error!("Failed to read runtime file: {}", path);
    panic!("Failed to read runtime file: {}", path);
}

fn main() {
    env_logger::Builder::from_default_env()
        .filter_level(log::LevelFilter::Error)
        .init();

    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        error!("Usage: {} <action>", args[0]);
        return;
    }

    let mut pic = Pic::new();
    pic.action = args[1].clone();

    match pic.run() {
        Ok(file) => println!("{}", file),
        Err(e) => error!("Error: {}", e),
    }
}
