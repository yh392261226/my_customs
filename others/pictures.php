<?php
ini_set('display_error', 'off');
ini_set('error_reporting', '0');
/**
 * 用于iterm2 的背景随机更换
 *
 */
function getMyRuntime() {
	$output = shell_exec('cat $HOME/.myruntime');
	return trim($output);
}

class Pic {
	public $filedir = "";
	public $start   = 0;
	public $ext     = 'jpg';

	public $action;
	public $rand_num;
	public $currentpage;
	private $total;
	private $prepage;
	private $nextpage;
	private $currentpagefile = '';
	private $currentnamefile = '';

	public function __construct() {
		/*if (!$this->checkDir()) {
		exit('Error: Can not find the File dir!!!');
		}*/
		$myruntime             = getMyRuntime();
		$this->currentpagefile = $myruntime.'/tools/current_picture';
		$this->currentnamefile = $myruntime.'/tools/current_picturename';
		// echo $this->currentpagefile . '\n';
// 		echo $this->currentnamefile . '\n';
// 		exit();
		$this->getCurrentPageFromFile();
	}

	private function checkDir() {
		if (!is_dir($this->filedir)) {
			return false;
		}

		return true;
	}

	public function getFileLists() {
		$handler = opendir($this->filedir);
		$tmplist = array();
		while (($file = readdir($handler)) !== false) {
			$ext_array = array();
			$ext_array = explode('.', $file);
			$ext_last = end($ext_array);
			if (is_file($this->filedir.'/'.$file) && $ext_last == $this->ext) {
				$tmplist[] = $this->filedir.'/'.$file;
			}
		}
		$this->total     = count($tmplist);
		$this->filelists = $tmplist;
		closedir($handler);
	}

	private function getRandNum() {
		$this->rand_num = rand($this->start, $this->total);
	}

	private function getPrePage() {
		if ($this->currentpage <= 1) {
			$this->prepage = 1;
		} else {
			$this->prepage = $this->currentpage-1;
		}
	}

	private function getNextPage() {
		if ($this->currentpage >= $this->total) {
			$this->nextpage = $this->total;
		} else {
			$this->nextpage = $this->currentpage+1;
		}
	}

	public function run() {
		$this->getFileLists();
		switch ($this->action) {
			case 'pre':
				$this->getCurrentPageFromFile();
				$this->getPrePage();
				$this->currentpage = $this->prepage;
				$this->setCurrentPageToFile();
				return $this->filelists[$this->prepage];
				break;
			case 'next':
				$this->getCurrentPageFromFile();
				$this->getNextPage();
				$this->currentpage = $this->nextpage;
				$this->setCurrentPageToFile();
				return $this->filelists[$this->nextpage];
				break;
			case 'rand':
				$this->getRandNum();
				$this->currentpage = $this->rand_num;
				$this->setCurrentPageToFile();
				return $this->filelists[$this->rand_num];
				break;
			default:
				return $this->filelists;
				break;
		}
	}

	private function setCurrentPageToFile() {
		file_put_contents($this->currentpagefile, $this->currentpage);//记录文件在数组中的键
		file_put_contents($this->currentnamefile, $this->filelists[$this->currentpage]);//记录文件名
	}

	private function getCurrentPageFromFile() {
		if (file_exists($this->currentpagefile)) {
			$tmpnum = file_get_contents($this->currentpagefile);
		} else {
			$tmpnum = 1;
		}
		$this->currentpage = $tmpnum;
	}
}

$getpath      = getMyRuntime();
$MYRUNTIME    = $getpath . '/pictures';
$pic          = new Pic();
$pic->filedir = $MYRUNTIME;
$pic->action  = $argv[1];
echo $pic->run();
