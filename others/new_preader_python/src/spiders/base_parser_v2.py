"""
书籍网站解析器公共基类 - 配置驱动版本
基于属性配置的灵活解析器架构
"""

import re
import time
import requests
import os
from typing import Dict, Any, List, Optional, Callable
from urllib.parse import urljoin
from src.utils.logger import get_logger

logger = get_logger(__name__)

class BaseParser:
    """书籍网站解析器公共基类 - 配置驱动版本"""
    
    # 子类必须定义的属性
    name: str = "未知解析器"
    description: str = "未知解析器描述"
    base_url: str = ""
    
    # 配置属性 - 子类可以重写这些属性
    title_reg: List[str] = []  # 标题正则表达式列表
    content_reg: List[str] = []  # 内容正则表达式列表
    status_reg: List[str] = []  # 状态正则表达式列表
    book_type: List[str] = ["短篇", "多章节", "短篇+多章节", "内容页内分页"]  # 支持的书籍类型
    
    # 繁体转简体映射表
    TRADITIONAL_TO_SIMPLIFIED = {}

    # 内容页内分页相关配置
    content_page_link_reg: List[str] = []  # 内容页面链接正则表达式
    next_page_link_reg: List[str] = []  # 下一页链接正则表达式
    
    # 处理函数配置
    after_crawler_func: List[str] = []  # 爬取后处理函数名列表
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置，格式为 {'enabled': bool, 'proxy_url': str}
            novel_site_name: 从数据库获取的网站名称，用于作者信息
        """
        self.session = requests.Session()
        self.proxy_config = proxy_config or {'enabled': False, 'proxy_url': ''}
        self.chapter_count = 0
        # 保存从数据库获取的网站名称，用于作者信息
        self.novel_site_name = novel_site_name or self.name
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })

        # 初始化繁简转换映射表
        self._init_traditional_simplified_mapping()

    def _init_traditional_simplified_mapping(self):
        """初始化繁简转换映射表"""
        # 使用chinese.js中的正确映射表
        simplified  = '锕锿皑嗳蔼霭爱嫒碍暧瑷庵谙鹌鞍埯铵暗暗翱翱鳌鳌袄媪岙奥骜钯坝坝罢鲅霸摆呗败稗颁坂板钣办绊帮绑榜膀谤镑龅褒宝饱鸨褓报鲍杯杯鹎贝狈备背钡悖惫辈鞴奔奔贲锛绷绷逼秕笔币毕闭哔荜毙铋筚滗痹跸辟弊边笾编鳊贬变缏辩辫标飑骠膘镖飙飙飚镳表鳔鳖鳖别别瘪宾宾傧滨缤槟镔濒摈殡膑髌鬓鬓冰饼禀并并并拨剥钵钵饽驳驳钹铂博鹁钸卜补布钚财采采采彩睬踩参参参骖残蚕惭惭惨黪灿仓伧沧苍舱操艹册侧厕厕恻测策策层插馇锸查察镲诧钗侪虿觇掺搀婵谗禅馋缠蝉镡产产谄铲铲阐蒇冁忏颤伥阊鲳长肠苌尝尝偿厂厂场场怅畅钞车砗扯彻尘陈谌谌碜碜闯衬称龀趁榇谶柽蛏铛撑枨诚乘铖惩塍澄骋吃鸱痴驰迟齿耻饬炽敕冲冲虫宠铳俦帱绸畴筹酬酬酬踌雠雠丑瞅出刍厨锄锄雏橱蹰础储处处绌触传船钏囱疮窗窗窗床创怆捶棰锤锤春纯唇莼莼淳鹑醇绰辍龊词辞辞鹚鹚糍赐从匆匆苁枞葱骢聪丛丛凑辏粗粗蹴撺镩蹿窜篡脆村鹾锉错哒达沓鞑呆绐带玳贷单担郸殚瘅箪胆掸诞啖啖弹惮当当当裆挡挡党谠凼砀荡荡档导岛捣捣祷焘盗锝德灯邓凳镫堤镝籴敌涤觌诋抵抵递谛缔蒂颠巅癫点电垫钿淀雕雕雕鲷吊钓调铞谍喋叠叠叠蝶鲽钉顶订碇碇锭丢铥东冬岽岽鸫动冻峒栋胨兜斗斗斗钭豆窦读渎渎椟椟牍犊黩独笃赌睹妒镀端断缎煅锻簖队对兑怼镦吨墩趸炖钝顿遁夺铎朵垛缍堕跺讹讹峨锇鹅鹅额婀厄厄轭垩恶恶饿谔阏萼腭锷鹗颚鳄鳄儿鸸鲕尔迩饵铒贰发发罚罚阀法珐帆翻翻凡矾钒烦繁泛泛饭范贩钫鲂仿仿仿访纺飞绯鲱诽废费痱镄纷氛坟奋偾愤粪鲼丰风沣枫疯砜峰锋冯缝讽凤佛夫肤麸麸凫绂绋辐幞呒抚俯俯辅讣妇负附驸复复赋缚鲋赙鳆钆嘎该赅丐丐钙盖概干干杆尴尴秆赶绀赣冈刚岗纲肛钢杠戆皋槔糕缟稿镐诰锆纥胳鸽搁歌阁镉个个铬给亘耕赓绠鲠鲠宫躬龚巩贡沟钩钩缑构构诟购够觏轱鸪毂鹘诂谷钴蛊鹄鼓顾雇锢鲴刮鸹剐诖挂拐拐怪关关观鳏馆馆管管贯惯掼鹳罐广犷归妫妫龟规规闺瑰鲑轨匦诡刽刿柜贵鳜衮绲辊滚鲧鲧呙埚锅蝈国国帼掴果椁过铪骇顸函韩汉悍焊焊颔绗颃蚝嗥号皓皓颢灏诃合合和阂核盍颌阖贺鹤恒横轰哄红闳荭鸿黉讧糇鲎呼呼呼轷胡胡壶鹕糊浒户冱护沪鹱花花华哗哗骅铧划画话桦怀坏欢欢獾还环锾缳缓奂唤换涣焕痪鲩黄鳇恍谎诙咴挥晖珲辉辉徽回回回回蛔蛔蛔蛔汇汇汇会讳哕浍绘荟诲桧烩贿秽缋毁毁毁昏荤阍浑馄诨锪钬货获获祸镬讥击叽饥饥机玑矶鸡鸡迹迹积绩绩缉赍赍跻齑羁级极楫辑几虮挤计记纪际剂哜济继觊蓟霁鲚鲫骥夹夹浃家镓郏荚铗蛱颊贾钾价驾戋奸坚歼间艰监笺笺缄缣鲣鹣鞯拣枧俭茧捡笕减检睑裥锏简谫戬碱碱见饯剑剑荐贱涧舰渐谏溅践鉴鉴鉴键槛姜将浆僵缰缰讲奖桨蒋绛酱娇浇骄胶鲛鹪侥挢绞饺矫脚铰搅剿缴叫峤轿较阶阶疖秸节讦劫劫劫杰诘洁结颉鲒届诫斤仅卺紧谨锦馑尽尽劲进荩晋烬赆赆缙觐泾经茎荆惊鲸阱刭颈净弪径径胫痉竞靓静镜迥炯纠鸠阄揪韭旧厩厩救鹫驹锔局局举举榉龃讵钜剧惧据飓锯窭屦鹃镌镌卷锩倦桊狷绢隽眷决诀珏绝觉谲橛镢镢军钧皲俊浚骏咔开锎凯剀垲恺铠慨锴忾龛坎侃阚瞰糠糠闶炕钪考铐轲疴钶颏颗壳咳克克课骒缂锞肯垦恳坑铿抠眍叩扣寇库绔喾裤夸块侩郐哙狯脍宽髋款诓诳邝圹纩况旷矿矿贶亏岿窥窥匮愦愧溃蒉馈馈篑聩坤昆昆锟鲲捆捆阃困扩阔阔腊蜡辣来崃徕涞莱铼赉睐赖赖濑癞籁兰岚拦栏婪阑蓝谰澜褴斓篮镧览揽缆榄懒懒烂滥琅锒螂阆捞劳唠崂痨铹铑涝耢乐鳓缧镭诔垒泪类累棱厘梨狸离骊犁鹂漓缡蓠璃璃鲡篱藜礼里里逦锂鲤鳢历历历厉丽励呖坜沥苈枥疠隶隶俪栎疬疬荔轹郦栗砺砾莅莅粝蛎跞雳俩奁奁奁奁连帘怜涟莲联裢廉鲢镰敛敛琏脸裣蔹练娈炼炼恋殓链潋凉梁粮两魉谅辆辽疗缭镣鹩钌猎邻邻临淋辚磷磷鳞麟凛廪懔檩吝赁蔺躏灵灵岭凌铃棂棂绫菱龄鲮领溜刘浏留琉琉馏骝瘤镏柳柳绺锍鹨龙咙泷茏栊珑胧砻笼聋陇垄垄拢娄偻喽蒌楼耧蝼髅嵝搂篓瘘瘘镂噜撸卢庐芦垆垆泸炉炉栌胪轳鸬舻颅鲈卤卤虏掳鲁橹橹橹镥陆录赂辂渌禄滤戮辘鹭氇驴闾榈吕侣稆铝屡缕褛虑绿孪峦挛栾鸾脔滦銮乱略锊抡仑仑伦囵沦纶轮论罗罗猡脶萝逻椤锣箩骡骡镙裸裸泺络荦骆妈嬷麻蟆马犸玛码蚂杩骂骂唛吗买荬劢迈麦卖脉脉颟蛮馒瞒鳗满螨谩缦镘猫牦牦锚铆冒贸帽帽么没梅梅镅鹛霉镁门扪钔闷焖懑们蒙蒙蒙锰梦弥弥祢猕谜芈眯觅觅秘幂谧绵绵黾缅腼面面面鹋缈妙庙咩灭蔑珉缗缗闵泯闽悯愍鳘鸣铭谬缪谟馍馍模殁蓦镆谋亩钼幕拿拿镎内纳钠乃乃奶难楠楠馕挠铙蛲垴恼脑闹闹讷馁嫩铌霓鲵你拟昵腻鲇鲶捻辇撵念娘酿鸟茑袅袅袅捏陧聂啮啮嗫镊镍颞蹑孽宁咛拧狞柠聍泞纽钮农农侬哝浓脓弄驽钕疟暖暖傩诺锘讴欧殴瓯鸥呕怄沤盘盘蹒庞刨刨狍炮炮疱胚赔锫佩辔喷鹏碰碰纰铍毗罴骈谝骗骗缥飘飘贫嫔频颦评凭凭苹瓶鲆钋泼颇钷迫仆扑铺铺镤朴谱镨凄凄栖桤戚戚齐脐颀骐骑棋棋蛴旗蕲鳍岂启启绮气讫弃荠碛憩千扦迁佥钎牵悭铅谦愆签签骞荨钤钱钳乾乾潜浅肷谴缱堑椠呛羌戗枪跄锖锵镪强强墙墙嫱蔷樯樯抢羟襁襁炝硗硗跷锹锹缲乔侨荞桥谯憔憔鞒诮峭窍翘窃惬箧锲亲钦琴勤锓寝吣揿揿氢轻倾鲭苘顷请庆穷茕琼丘秋秋鳅鳅虬球赇巯区曲曲岖诎驱驱躯趋鸲癯龋阒觑觑觑权诠辁铨蜷颧绻劝却悫悫确阕阙鹊榷裙裙群冉让荛饶桡扰娆绕热认纫妊轫韧韧饪绒绒绒荣嵘蝾融冗铷颥缛软软蕊蕊蕊锐睿闰润箬洒飒萨腮鳃赛毵伞伞糁馓颡丧骚缫鳋扫涩涩啬铯穑杀纱铩鲨筛晒删姗钐膻闪陕讪骟缮膳赡鳝鳝伤殇觞垧赏绱烧绍赊蛇舍厍设慑慑摄滠绅诜审审谂婶渖肾渗升升声胜渑绳圣剩尸师虱诗狮湿湿酾鲺时识实蚀埘莳鲥驶势视视视试饰是柿贳适轼铈谥谥释寿寿兽绶书纾枢倏倏疏摅输赎薯术树竖竖庶数漱帅闩双谁税顺说说烁铄硕丝咝鸶缌蛳厮锶似祀饲驷俟松怂耸讼诵颂搜馊飕锼擞薮苏苏苏稣诉肃谡溯溯酸虽绥随岁岁谇孙狲荪飧损笋挲蓑缩唢琐锁它铊塔獭鳎挞闼骀台台台抬鲐态钛贪摊滩瘫坛坛坛坛坛昙谈锬谭袒钽叹叹赕汤铴镗饧糖傥烫趟涛绦绦绦掏韬鼗鼗讨铽腾誊藤锑绨啼缇鹈题蹄体体屉剃剃阗条龆鲦眺粜铫贴铁铁铁厅厅听听烃铤同铜统筒恸偷偷头秃图涂涂钍兔团团抟颓颓颓腿蜕饨臀托拖脱驮驼鸵鼍椭拓箨洼娲蛙袜袜腽弯湾纨玩顽挽绾碗碗万亡网往辋望为为韦围帏沩沩违闱涠维潍伟伪伪纬苇炜玮诿韪鲔卫卫谓喂喂猬温纹闻蚊蚊阌吻稳问瓮瓮挝涡莴窝蜗卧龌乌污污邬呜诬钨无吴芜坞坞妩妩庑忤怃鹉务误骛雾鹜诶牺晰溪锡嘻膝习席袭觋玺铣戏戏系系饩细郄阋舄虾侠峡狭硖辖辖吓厦仙纤纤籼莶跹锨鲜闲闲弦贤咸娴娴衔衔痫鹇鹇鹇显险猃蚬藓县岘苋现线线宪馅羡献乡乡芗厢缃骧镶详享响饷飨鲞向向项枭哓骁绡萧销潇箫嚣嚣晓筱效效啸啸蝎协邪胁胁挟谐携携撷缬鞋写泄泻绁绁绁亵谢蟹欣锌衅兴陉幸凶汹胸修鸺馐绣绣锈锈须须顼虚嘘许诩叙叙恤恤勖绪续婿溆轩谖喧萱萱萱萱悬旋璇选癣绚铉楦靴学泶鳕谑勋勋埙埙熏寻巡驯询浔鲟训讯徇逊丫压鸦鸦桠鸭哑痖亚讶垭娅氩咽恹恹烟胭阉腌讠闫严岩岩岩盐阎颜颜檐兖俨厣演魇鼹厌彦砚艳艳验验谚焰雁滟滟酽谳餍燕燕燕赝赝鸯扬扬扬阳杨炀疡养痒样夭尧肴轺窑窑谣摇遥瑶鳐药药鹞耀爷铘野野业叶页邺夜晔烨烨谒靥医医咿铱仪诒迤饴贻移遗颐彝彝钇舣蚁蚁义亿忆艺议异呓呓译峄怿绎诣驿轶谊缢瘗镒翳镱因阴阴荫荫殷铟喑堙吟淫淫银龈饮隐瘾应莺莺婴嘤撄缨罂罂樱璎鹦鹰茔荥荧莹萤营萦滢蓥潆蝇赢颍颖瘿映哟佣拥痈雍墉镛鳙咏涌恿恿踊优忧犹邮莜莸铀游鱿铕佑诱纡余欤鱼娱谀渔嵛逾觎舆与伛屿俣语龉驭吁吁妪饫郁狱钰预欲谕阈御鹆愈愈蓣誉鹬鸢鸳渊员园圆缘鼋猿猿辕橼远愿约岳钥钥钥悦钺阅阅跃粤云匀纭芸郧氲陨殒运郓恽晕酝酝愠韫韵蕴匝杂杂灾灾灾载簪咱咱攒攒攒趱暂赞赞赞錾瓒赃赃赃驵脏脏葬糟凿枣灶皂唣噪则择泽责啧帻箦赜贼谮缯锃赠揸齄扎扎札札轧闸闸铡诈栅榨斋债沾毡毡谵斩盏崭辗占战栈绽骣张獐涨帐胀账钊诏赵棹照哲辄蛰谪谪辙锗这浙鹧贞针针侦浈珍桢砧祯诊轸缜阵鸩赈镇争征峥挣狰钲睁铮筝证证诤郑帧症卮织栀执侄侄职絷跖踯只只址纸轵志制帙帙帜质栉挚致贽轾掷鸷滞骘稚稚置觯踬终钟钟钟肿种冢众众诌周轴帚纣咒绉昼荮皱骤朱诛诸猪铢槠潴橥烛属煮嘱瞩伫伫苎注贮驻筑铸箸专砖砖砖颛转啭赚撰馔妆妆庄桩装壮状骓锥坠缀缒赘谆准桌斫斫斫浊诼镯镯兹兹赀资缁谘辎锱龇鲻姊渍眦综棕踪鬃鬃总总偬纵粽邹驺诹鲰镞诅组躜缵纂钻钻罪樽鳟'
        traditional = '錒鎄皚噯藹靄愛嬡礙曖璦庵諳鵪鞍垵銨暗暗翱翱鼇鼇襖媼嶴奧驁鈀壩壩罷鮁霸擺唄敗稗頒阪板鈑辦絆幫綁榜膀謗鎊齙褒寶飽鴇褓報鮑杯杯鵯貝狽備背鋇悖憊輩韝奔奔賁錛繃繃逼秕筆幣畢閉嗶蓽斃鉍篳潷痹蹕辟弊邊籩編鯿貶變緶辯辮標颮驃膘鏢飆飆飆鑣表鰾鱉鱉別別癟賓賓儐濱繽檳鑌瀕擯殯臏髕鬢鬢冰餅稟並並並撥剝缽缽餑駁駁鈸鉑博鵓鈽蔔補布鈈財采采采彩睬踩參參參驂殘蠶慚慚慘黲燦倉傖滄蒼艙操艸冊側廁廁惻測策策層插餷鍤查察鑔詫釵儕蠆覘摻攙嬋讒禪饞纏蟬鐔產產諂鏟鏟闡蕆囅懺顫倀閶鯧長腸萇嘗嘗償廠廠場場悵暢鈔車硨扯徹塵陳諶諶磣磣闖襯稱齔趁櫬讖檉蟶鐺撐棖誠乘鋮懲塍澄騁吃鴟癡馳遲齒恥飭熾敕衝衝蟲寵銃儔幬綢疇籌酬酬酬躊讎讎醜瞅出芻廚鋤鋤雛櫥躕礎儲處處絀觸傳船釧囪瘡窗窗窗床創愴捶棰錘錘春純唇蓴蓴淳鶉醇綽輟齪詞辭辭鶿鶿糍賜從匆匆蓯樅蔥驄聰叢叢湊輳粗粗蹴攛鑹躥竄篡脆村鹺銼錯噠達遝韃呆紿帶玳貸單擔鄲殫癉簞膽撣誕啖啖彈憚當當當襠擋擋黨讜氹碭蕩蕩檔導島搗搗禱燾盜鍀德燈鄧凳鐙堤鏑糴敵滌覿詆抵抵遞諦締蒂顛巔癲點電墊鈿澱雕雕雕鯛吊釣調銱諜喋疊疊疊蝶鰈釘頂訂碇碇錠丟銩東冬崠崠鶇動凍峒棟腖兜鬥鬥鬥鈄豆竇讀瀆瀆櫝櫝牘犢黷獨篤賭睹妒鍍端斷緞煆鍛籪隊對兌懟鐓噸墩躉燉鈍頓遁奪鐸朵垛綞墮跺訛訛峨鋨鵝鵝額婀厄厄軛堊惡惡餓諤閼萼齶鍔鶚顎鱷鱷兒鴯鮞爾邇餌鉺貳發發罰罰閥法琺帆翻翻凡礬釩煩繁泛泛飯範販鈁魴仿仿仿訪紡飛緋鯡誹廢費痱鐨紛氛墳奮僨憤糞鱝豐風灃楓瘋碸峰鋒馮縫諷鳳佛夫膚麩麩鳧紱紼輻襆嘸撫俯俯輔訃婦負附駙複複賦縛鮒賻鰒釓嘎該賅丐丐鈣蓋概幹幹杆尷尷稈趕紺贛岡剛崗綱肛鋼杠戇皋槔糕縞稿鎬誥鋯紇胳鴿擱歌閣鎘個個鉻給亙耕賡綆鯁鯁宮躬龔鞏貢溝鉤鉤緱構構詬購夠覯軲鴣轂鶻詁穀鈷蠱鵠鼓顧雇錮鯝刮鴰剮詿掛拐拐怪關關觀鰥館館管管貫慣摜鸛罐廣獷歸媯媯龜規規閨瑰鮭軌匭詭劊劌櫃貴鱖袞緄輥滾鯀鯀咼堝鍋蟈國國幗摑果槨過鉿駭頇函韓漢悍焊焊頷絎頏蠔嗥號皓皓顥灝訶合合和閡核盍頜闔賀鶴恒橫轟哄紅閎葒鴻黌訌餱鱟呼呼呼軤胡胡壺鶘糊滸戶冱護滬鸌花花華嘩嘩驊鏵劃畫話樺懷壞歡歡獾還環鍰繯緩奐喚換渙煥瘓鯇黃鰉恍謊詼噅揮暉琿輝輝徽回回回回蛔蛔蛔蛔匯匯匯會諱噦澮繪薈誨檜燴賄穢繢毀毀毀昏葷閽渾餛諢鍃鈥貨獲獲禍鑊譏擊嘰饑饑機璣磯雞雞跡跡積績績緝齎齎躋齏羈級極楫輯幾蟣擠計記紀際劑嚌濟繼覬薊霽鱭鯽驥夾夾浹家鎵郟莢鋏蛺頰賈鉀價駕戔奸堅殲間艱監箋箋緘縑鰹鶼韉揀梘儉繭撿筧減檢瞼襇鐧簡譾戩堿堿見餞劍劍薦賤澗艦漸諫濺踐鑒鑒鑒鍵檻薑將漿僵韁韁講獎槳蔣絳醬嬌澆驕膠鮫鷦僥撟絞餃矯腳鉸攪剿繳叫嶠轎較階階癤秸節訐劫劫劫傑詰潔結頡鮚屆誡斤僅巹緊謹錦饉盡盡勁進藎晉燼贐贐縉覲涇經莖荊驚鯨阱剄頸淨弳徑徑脛痙競靚靜鏡迥炯糾鳩鬮揪韭舊廄廄救鷲駒鋦局局舉舉櫸齟詎钜劇懼據颶鋸窶屨鵑鐫鐫卷錈倦棬狷絹雋眷決訣玨絕覺譎橛钁钁軍鈞皸俊浚駿哢開鉲凱剴塏愷鎧慨鍇愾龕坎侃闞瞰糠糠閌炕鈧考銬軻屙鈳頦顆殼咳克克課騍緙錁肯墾懇坑鏗摳瞘叩扣寇庫絝嚳褲誇塊儈鄶噲獪膾寬髖款誆誑鄺壙纊況曠礦礦貺虧巋窺窺匱憒愧潰蕢饋饋簣聵坤昆昆錕鯤捆捆閫困擴闊闊臘蠟辣來崍徠淶萊錸賚睞賴賴瀨癩籟蘭嵐攔欄婪闌藍讕瀾襤斕籃鑭覽攬纜欖懶懶爛濫琅鋃螂閬撈勞嘮嶗癆鐒銠澇耮樂鰳縲鐳誄壘淚類累棱厘梨狸離驪犁鸝漓縭蘺璃璃鱺籬藜禮裏裏邐鋰鯉鱧歷歷曆厲麗勵嚦壢瀝藶櫪癘隸隸儷櫟鬁鬁荔轢酈栗礪礫蒞蒞糲蠣躒靂倆奩奩奩奩連簾憐漣蓮聯褳廉鰱鐮斂斂璉臉襝蘞練孌煉煉戀殮鏈瀲涼梁糧兩魎諒輛遼療繚鐐鷯釕獵鄰鄰臨淋轔磷磷鱗麟凜廩懍檁吝賃藺躪靈靈嶺淩鈴欞欞綾菱齡鯪領溜劉瀏留琉琉餾騮瘤鎦柳柳綹鋶鷚龍嚨瀧蘢櫳瓏朧礱籠聾隴壟壟攏婁僂嘍蔞樓耬螻髏嶁摟簍瘺瘺鏤嚕擼盧廬蘆壚壚瀘爐爐櫨臚轤鸕艫顱鱸鹵鹵虜擄魯櫓櫓櫓鑥陸錄賂輅淥祿濾戮轆鷺氌驢閭櫚呂侶穭鋁屢縷褸慮綠孿巒攣欒鸞臠灤鑾亂略鋝掄侖侖倫圇淪綸輪論羅羅玀腡蘿邏欏鑼籮騾騾鏍裸裸濼絡犖駱媽嬤麻蟆馬獁瑪碼螞榪罵罵嘜嗎買蕒勱邁麥賣脈脈顢蠻饅瞞鰻滿蟎謾縵鏝貓犛犛錨鉚冒貿帽帽麼沒梅梅鋂鶥黴鎂門捫鍆悶燜懣們濛濛蒙錳夢彌彌禰獼謎羋眯覓覓秘冪謐綿綿黽緬靦面面面鶓緲妙廟咩滅蔑瑉緡緡閔泯閩憫湣鰵鳴銘謬繆謨饃饃模歿驀鏌謀畝鉬幕拿拿錼內納鈉乃乃奶難楠楠饢撓鐃蟯堖惱腦鬧鬧訥餒嫩鈮霓鯢你擬昵膩鯰鯰撚輦攆念娘釀鳥蔦嫋嫋嫋捏隉聶齧齧囁鑷鎳顳躡孽寧嚀擰獰檸聹濘紐鈕農農儂噥濃膿弄駑釹瘧暖暖儺諾鍩謳歐毆甌鷗嘔慪漚盤盤蹣龐刨刨麅炮炮皰胚賠錇佩轡噴鵬碰碰紕鈹毗羆駢諞騙騙縹飄飄貧嬪頻顰評憑憑蘋瓶鮃釙潑頗鉕迫僕撲鋪鋪鏷樸譜鐠淒淒棲榿戚戚齊臍頎騏騎棋棋蠐旗蘄鰭豈啟啟綺氣訖棄薺磧憩千扡遷僉釺牽慳鉛謙愆簽簽騫蕁鈐錢鉗乾乾潛淺膁譴繾塹槧嗆羌戧槍蹌錆鏘鏹強強牆牆嬙薔檣檣搶羥繈繈熗磽磽蹺鍬鍬繰喬僑蕎橋譙憔憔鞽誚峭竅翹竊愜篋鍥親欽琴勤鋟寢唚撳撳氫輕傾鯖檾頃請慶窮煢瓊丘秋秋鰍鰍虯球賕巰區曲曲嶇詘驅驅軀趨鴝臒齲闃覷覷覷權詮輇銓蜷顴綣勸卻愨愨確闋闕鵲榷裙裙群冉讓蕘饒橈擾嬈繞熱認紉妊軔韌韌飪絨絨絨榮嶸蠑融冗銣顬縟軟軟蕊蕊蕊銳睿閏潤箬灑颯薩腮鰓賽毿傘傘糝饊顙喪騷繅鰠掃澀澀嗇銫穡殺紗鎩鯊篩曬刪姍釤膻閃陝訕騸繕膳贍鱔鱔傷殤觴坰賞緔燒紹賒蛇舍厙設懾懾攝灄紳詵審審諗嬸瀋腎滲升升聲勝澠繩聖剩屍師虱詩獅濕濕釃鯴時識實蝕塒蒔鰣駛勢視視視試飾是柿貰適軾鈰諡諡釋壽壽獸綬書紓樞倏倏疏攄輸贖薯術樹豎豎庶數漱帥閂雙誰稅順說說爍鑠碩絲噝鷥緦螄廝鍶似祀飼駟俟松慫聳訟誦頌搜餿颼鎪擻藪蘇蘇蘇穌訴肅謖溯溯酸雖綏隨歲歲誶孫猻蓀飧損筍挲蓑縮嗩瑣鎖它鉈塔獺鰨撻闥駘台台台抬鮐態鈦貪攤灘癱壇壇壇壇壇曇談錟譚袒鉭歎歎賧湯鐋鏜餳糖儻燙趟濤絛絛絛掏韜鞀鞀討鋱騰謄藤銻綈啼緹鵜題蹄體體屜剃剃闐條齠鰷眺糶銚貼鐵鐵鐵廳廳聽聽烴鋌同銅統筒慟偷偷頭禿圖塗塗釷兔團團摶頹頹頹腿蛻飩臀托拖脫馱駝鴕鼉橢拓籜窪媧蛙襪襪膃彎灣紈玩頑挽綰碗碗萬亡網往輞望為為韋圍幃溈溈違闈潿維濰偉偽偽緯葦煒瑋諉韙鮪衛衛謂喂喂蝟溫紋聞蚊蚊閿吻穩問甕甕撾渦萵窩蝸臥齷烏汙汙鄔嗚誣鎢無吳蕪塢塢嫵嫵廡忤憮鵡務誤騖霧鶩誒犧晰溪錫嘻膝習席襲覡璽銑戲戲系系餼細郤鬩舄蝦俠峽狹硤轄轄嚇廈仙纖纖秈薟躚鍁鮮閑閑弦賢鹹嫻嫻銜銜癇鷳鷳鷳顯險獫蜆蘚縣峴莧現線線憲餡羨獻鄉鄉薌廂緗驤鑲詳享響餉饗鯗向向項梟嘵驍綃蕭銷瀟簫囂囂曉筱效效嘯嘯蠍協邪脅脅挾諧攜攜擷纈鞋寫泄瀉絏絏絏褻謝蟹欣鋅釁興陘幸凶洶胸修鵂饈繡繡鏽鏽須須頊虛噓許詡敘敘恤恤勖緒續婿漵軒諼喧萱萱萱萱懸旋璿選癬絢鉉楦靴學澩鱈謔勳勳塤塤熏尋巡馴詢潯鱘訓訊徇遜丫壓鴉鴉椏鴨啞瘂亞訝埡婭氬咽懨懨煙胭閹醃訁閆嚴岩岩岩鹽閻顏顏簷兗儼厴演魘鼴厭彥硯豔豔驗驗諺焰雁灩灩釅讞饜燕燕燕贗贗鴦揚揚揚陽楊煬瘍養癢樣夭堯肴軺窯窯謠搖遙瑤鰩藥藥鷂耀爺鋣野野業葉頁鄴夜曄燁燁謁靨醫醫咿銥儀詒迤飴貽移遺頤彝彝釔艤蟻蟻義億憶藝議異囈囈譯嶧懌繹詣驛軼誼縊瘞鎰翳鐿因陰陰蔭蔭殷銦喑堙吟淫淫銀齦飲隱癮應鶯鶯嬰嚶攖纓罌罌櫻瓔鸚鷹塋滎熒瑩螢營縈瀅鎣瀠蠅贏潁穎癭映喲傭擁癰雍墉鏞鱅詠湧恿恿踴優憂猶郵蓧蕕鈾遊魷銪佑誘紆餘歟魚娛諛漁崳逾覦輿與傴嶼俁語齬馭吁吁嫗飫鬱獄鈺預欲諭閾禦鵒愈愈蕷譽鷸鳶鴛淵員園圓緣黿猿猿轅櫞遠願約嶽鑰鑰鑰悅鉞閱閱躍粵雲勻紜芸鄖氳隕殞運鄆惲暈醞醞慍韞韻蘊匝雜雜災災災載簪咱咱攢攢攢趲暫贊贊贊鏨瓚贓贓贓駔髒髒葬糟鑿棗灶皂唕噪則擇澤責嘖幘簀賾賊譖繒鋥贈摣齇紮紮劄劄軋閘閘鍘詐柵榨齋債沾氈氈譫斬盞嶄輾占戰棧綻驏張獐漲帳脹賬釗詔趙棹照哲輒蟄謫謫轍鍺這浙鷓貞針針偵湞珍楨砧禎診軫縝陣鴆賑鎮爭征崢掙猙鉦睜錚箏證證諍鄭幀症卮織梔執侄侄職縶蹠躑只只址紙軹志制帙帙幟質櫛摯致贄輊擲鷙滯騭稚稚置觶躓終鐘鐘鐘腫種塚眾眾謅周軸帚紂咒縐晝葤皺驟朱誅諸豬銖櫧瀦櫫燭屬煮囑矚佇佇苧注貯駐築鑄箸專磚磚磚顓轉囀賺撰饌妝妝莊樁裝壯狀騅錐墜綴縋贅諄准桌斫斫斫濁諑鐲鐲茲茲貲資緇諮輜錙齜鯔姊漬眥綜棕蹤鬃鬃總總傯縱粽鄒騶諏鯫鏃詛組躦纘纂鑽鑽罪樽鱒'

# 验证字
        
        # 创建映射字典
        self.TRADITIONAL_TO_SIMPLIFIED = dict(zip(traditional, simplified))
        
        # # 添加一些额外的常见映射，确保覆盖更多繁体字
        # additional_mappings = {
        #     '鬱': '郁',
        #     '週': '周', 
        #     '麵': '面',
        #     '黃': '黄',
        #     '國': '国',
        #     '體': '体',
        #     '學': '学',
        #     '灣': '湾',
        #     '龍': '龙',
        #     '鳳': '凤',
        #     '點': '点',
        #     '線': '线',
        #     '門': '门',
        #     '開': '开',
        #     '關': '关'
        # }
        
        # # 更新映射表
        # self.TRADITIONAL_TO_SIMPLIFIED.update(additional_mappings)

    # 繁简转换
    def _convert_traditional_to_simplified(self, text: str) -> str:
        """
        将繁体中文转换为简体中文
        
        Args:
            text: 包含繁体中文的文本
            
        Returns:
            转换为简体中文的文本
        """
        try:
            # 使用映射表进行字符替换
            converted_text = []
            for char in text:
                if char in self.TRADITIONAL_TO_SIMPLIFIED:
                    converted_text.append(self.TRADITIONAL_TO_SIMPLIFIED[char])
                else:
                    converted_text.append(char)
            return ''.join(converted_text)
        except Exception as e:
            logger.warning(f"繁体转简体失败: {e}")
            return text
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL
        子类可以重写此方法来自定义URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/b/{novel_id}"
    
    def _get_url_content(self, url: str, max_retries: int = 5) -> Optional[str]:
        """
        获取URL内容，支持四层反爬虫绕过策略
        
        策略层级：
        1. 普通请求 (requests)
        2. Cloudscraper 绕过
        3. Selenium 浏览器模拟
        4. Playwright 高级反爬虫处理
        
        Args:
            url: 目标URL
            max_retries: 最大重试次数
            
        Returns:
            页面内容或None
        """
        proxies = None
        if self.proxy_config.get('enabled', False):
            proxy_url = self.proxy_config.get('proxy_url', '')
            if proxy_url:
                proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
        
        for attempt in range(max_retries):
            try:
                # 首先尝试普通请求 - 增加超时时间
                response = self.session.get(url, proxies=proxies, timeout=(15, 30))  # 连接15s，读取30s
                if response.status_code == 200:
                    # 检查内容是否为反爬虫页面
                    content = response.text
                    
                    # 检测 Cloudflare Turnstile 等高级反爬虫机制
                    if self._detect_advanced_anti_bot(content):
                        logger.warning(f"检测到高级反爬虫机制，尝试使用 Playwright: {url}")
                        return self._get_url_content_with_playwright(url, proxies)
                    
                    response.encoding = 'utf-8'
                    return content
                    
                elif response.status_code == 404:
                    logger.warning(f"页面不存在: {url}")
                    return None
                elif response.status_code in [403, 429, 503]:  # 反爬虫相关状态码
                    logger.warning(f"检测到反爬虫限制 (HTTP {response.status_code})，尝试使用cloudscraper: {url}")
                    # 使用cloudscraper绕过反爬虫
                    return self._get_url_content_with_cloudscraper(url, proxies)
                else:
                    logger.warning(f"HTTP {response.status_code} 获取失败: {url}")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"第 {attempt + 1} 次请求失败: {url}, 错误: {e}")
                
                # 根据尝试次数选择不同的绕过策略
                if attempt == 0:  # 第一次失败：尝试 cloudscraper
                    try:
                        return self._get_url_content_with_cloudscraper(url, proxies)
                    except Exception as scraper_error:
                        logger.warning(f"cloudscraper也失败: {scraper_error}")
                elif attempt == 1:  # 第二次失败：尝试 selenium
                    try:
                        return self._selenium_request(url, proxies)
                    except Exception as selenium_error:
                        logger.warning(f"selenium也失败: {selenium_error}")
                else:  # 第三次及以后：尝试 playwright
                    try:
                        return self._get_url_content_with_playwright(url, proxies)
                    except Exception as playwright_error:
                        logger.warning(f"playwright也失败: {playwright_error}")
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
        
        logger.error(f"所有反爬虫策略都失败: {url}")
        return None
    
    def _detect_advanced_anti_bot(self, content: str) -> bool:
        """
        检测是否存在高级反爬虫机制（如 Cloudflare Turnstile）
        
        Args:
            content: 页面内容
            
        Returns:
            是否存在高级反爬虫机制
        """
        try:
            from .playwright_crawler import detect_cloudflare_turnstile_in_content
            return detect_cloudflare_turnstile_in_content(content)
        except ImportError:
            # 如果无法导入 playwright_crawler，使用基本检测
            turnstile_patterns = [
                r'challenges\.cloudflare\.com',
                r'cf-turnstile',
                r'data-sitekey',
                r'turnstile\.cloudflare\.com'
            ]
            
            for pattern in turnstile_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return True
            
            return False
    
    def _get_url_content_with_playwright(self, url: str, proxies: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        使用 Playwright 获取页面内容，专门处理高级反爬虫机制
        
        Args:
            url: 目标URL
            proxies: 代理配置
            
        Returns:
            页面内容或None
        """
        try:
            from .playwright_crawler import get_playwright_content
            
            # 使用 Playwright 获取内容
            return get_playwright_content(url, self.proxy_config, timeout=60, headless=True)
            
        except ImportError:
            logger.warning("playwright 库未安装，无法使用 Playwright 爬虫")
            return None
        except Exception as e:
            logger.warning(f"Playwright 获取页面内容失败: {url}, 错误: {e}")
            return None
    
    def _get_url_content_with_cloudscraper(self, url: str, proxies: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        使用cloudscraper绕过反爬虫限制获取URL内容
        
        Args:
            url: 目标URL
            proxies: 代理配置
            
        Returns:
            页面内容或None
        """
        try:
            import cloudscraper
            
            # 创建cloudscraper会话，使用更强大的配置
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'mobile': False
                },
                # 禁用SSL验证以解决可能的SSL错误
                ssl_verify=False,
                # 增加延迟以模拟真实用户行为
                delay=2
            )
            
            # 设置更真实的请求头
            scraper.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            })
            
            # 设置代理
            if proxies:
                scraper.proxies = proxies
            
            # 设置更长的超时时间
            response = scraper.get(url, timeout=30)
            
            if response.status_code == 200:
                response.encoding = 'utf-8'
                logger.info(f"cloudscraper成功绕过反爬虫限制: {url}")
                return response.text
            else:
                logger.warning(f"cloudscraper请求失败 (HTTP {response.status_code}): {url}")
                # 如果cloudscraper也失败，尝试使用requests直接请求但使用不同的User-Agent
                return self._fallback_request(url, proxies)
                
        except ImportError:
            logger.warning("cloudscraper库未安装，无法绕过反爬虫限制")
            return self._fallback_request(url, proxies)
        except Exception as e:
            logger.warning(f"cloudscraper请求异常: {e}")
            return self._fallback_request(url, proxies)
    
    def _fallback_request(self, url: str, proxies: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        备用请求方法，使用不同的User-Agent和策略
        
        Args:
            url: 目标URL
            proxies: 代理配置
            
        Returns:
            页面内容或None
        """
        try:
            # 创建新的会话，使用不同的User-Agent
            fallback_session = requests.Session()
            fallback_session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive'
            })
            
            # 禁用SSL验证
            fallback_session.verify = False
            
            # 设置代理
            if proxies:
                fallback_session.proxies = proxies
            
            response = fallback_session.get(url, timeout=15)
            
            if response.status_code == 200:
                response.encoding = 'utf-8'
                logger.info(f"备用请求成功: {url}")
                return response.text
            else:
                logger.warning(f"备用请求失败 (HTTP {response.status_code}): {url}")
                # 如果备用请求也失败，尝试使用selenium作为最后手段
                return self._selenium_request(url, proxies)
                
        except Exception as e:
            logger.warning(f"备用请求异常: {e}")
            # 如果备用请求异常，也尝试selenium
            return self._selenium_request(url, proxies)
    
    def _selenium_request(self, url: str, proxies: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        使用selenium + 浏览器指纹伪装作为最后的反爬虫绕过手段
        
        Args:
            url: 目标URL
            proxies: 代理配置
            
        Returns:
            页面内容或None
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.common.by import By
            import time
            
            # 配置Chrome选项进行浏览器指纹伪装
            chrome_options = Options()
            
            # 无头模式（可选，根据需求开启）
            # chrome_options.add_argument('--headless')
            
            # 禁用自动化检测
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 浏览器指纹伪装
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')
            chrome_options.add_argument('--disable-javascript')
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            
            # 设置用户代理
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')
            
            # 设置窗口大小模拟真实浏览器
            chrome_options.add_argument('--window-size=1920,1080')
            
            # 设置代理
            if proxies:
                proxy_url = proxies.get('http') or proxies.get('https')
                if proxy_url:
                    chrome_options.add_argument(f'--proxy-server={proxy_url}')
            
            # 使用webdriver-manager自动管理ChromeDriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            try:
                # 执行JavaScript脚本进一步伪装
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                # 访问目标URL
                driver.get(url)
                
                # 等待页面加载
                time.sleep(10)
                
                # 获取页面源代码
                page_source = driver.page_source
                
                if page_source and len(page_source) > 100:  # 确保有内容
                    logger.info(f"selenium成功获取页面内容: {url}")
                    return page_source
                else:
                    logger.warning(f"selenium获取的页面内容为空或过短: {url}")
                    return None
                    
            except Exception as e:
                logger.warning(f"selenium操作异常: {e}")
                return None
                
            finally:
                # 确保浏览器关闭
                try:
                    driver.quit()
                except:
                    pass
                
        except ImportError:
            logger.warning("selenium库未安装，无法使用浏览器指纹伪装")
            return None
        except Exception as e:
            logger.warning(f"selenium初始化异常: {e}")
            return None
    
    def _clean_html_content(self, html_content: str) -> str:
        """
        清理HTML内容，提取纯文本
        这是公共方法，所有解析器都可以使用
        
        Args:
            html_content: HTML内容
            
        Returns:
            清理后的纯文本
        """
        import html
        
        # 优先清除所有的<a></a>标签及其内容
        clean_text = re.sub(r'<a[^>]*>.*?</a>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
        # 先移除<style>标签及其内容
        clean_text = re.sub(r'<style[^>]*>.*?</style>', '', clean_text, flags=re.IGNORECASE | re.DOTALL)
        # 移除<script>标签及其内容
        clean_text = re.sub(r'<script[^>]*>.*?</script>', '', clean_text, flags=re.IGNORECASE | re.DOTALL)
        # 移除其他HTML标签
        clean_text = re.sub(r'<[^>]+>', '', clean_text)
        
        # 使用html.unescape解码所有HTML实体
        clean_text = html.unescape(clean_text)
        
        # 替换剩余的特殊空白字符
        clean_text = clean_text.replace('\xa0', ' ')
        
        # 清理多余空白字符
        clean_text = re.sub(r'\s+', ' ', clean_text)
        return clean_text.strip()
    
    def _extract_with_regex(self, content: str, regex_list: List[str]) -> str:
        """
        使用正则表达式列表提取内容
        按顺序尝试每个正则，返回第一个有内容的匹配结果
        
        Args:
            content: 要提取的内容
            regex_list: 正则表达式列表
            
        Returns:
            提取的内容
        """
        for regex in regex_list:
            matches = re.findall(regex, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                extracted = match.strip() if isinstance(match, str) else match[0].strip() if match else ""
                if extracted:  # 确保内容不是空的
                    return extracted
        return ""
    
    def _detect_book_type(self, content: str) -> str:
        """
        自动检测书籍类型（短篇/多章节/内容页内分页）
        子类可以重写此方法来自定义检测逻辑
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # 检测内容页内分页模式（如87nb网站）
        content_page_patterns = [
            r'开始阅读|开始阅读',
            r'<a[^>]*href="[^"]*ltxs[^"]*"[^>]*>',
            r'<a[^>]*rel="next"[^>]*>下一',
            r'下一章|下一页'
        ]
        
        for pattern in content_page_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return "内容页内分页"
        
        # 检测多章节的常见模式
        multi_chapter_patterns = [
            r'章节列表|chapter.*list',
            r'第\s*\d+\s*章',
            r'目录|contents',
            r'<div[^>]*class="[^"]*chapter[^"]*"[^>]*>',
            r'<ul[^>]*class="[^"]*chapters[^"]*"[^>]*>'
        ]
        
        for pattern in multi_chapter_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return "多章节"
        
        # 检测短篇的常见模式
        short_story_patterns = [
            r'短篇|short.*story',
            r'单篇|single.*chapter',
            r'全文|full.*text'
        ]
        
        for pattern in short_story_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return "短篇"
        
        # 默认返回短篇
        return "短篇"
    
    def _execute_after_crawler_funcs(self, content: str) -> str:
        """
        执行爬取后处理函数
        按照配置顺序执行处理函数
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        processed_content = content
        
        for func_name in self.after_crawler_func:
            if hasattr(self, func_name):
                func = getattr(self, func_name)
                if callable(func):
                    try:
                        processed_content = func(processed_content)
                    except Exception as e:
                        logger.warning(f"执行处理函数 {func_name} 失败: {e}")
        
        return processed_content
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页
        子类必须实现此方法
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        raise NotImplementedError("子类必须实现 parse_novel_list 方法")
    
    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """
        获取书籍首页的标题、简介与状态
        使用配置的正则表达式自动提取
        
        Args:
            novel_id: 小说ID
            
        Returns:
            包含标题、简介、状态的字典
        """
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)
        
        if not content:
            return None
        
        # 自动检测书籍类型
        book_type = self._detect_book_type(content)
        
        # 使用配置的正则提取标题
        title = self._extract_with_regex(content, self.title_reg)
        
        # 使用配置的正则提取状态
        status = self._extract_with_regex(content, self.status_reg)
        
        return {
            "title": title or "未知标题",
            "desc": f"{book_type}小说",
            "status": status or "未知状态"
        }
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        解析小说详情并抓取小说内容
        根据检测到的书籍类型自动选择处理方式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说详情信息
        """
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)
        
        if not content:
            raise Exception(f"无法获取小说页面: {novel_url}")
        
        # 自动检测书籍类型
        book_type = self._detect_book_type(content)
        
        # 提取标题
        title = self._extract_with_regex(content, self.title_reg)
        if not title:
            raise Exception("无法提取小说标题")
        
        print(f"开始处理 [ {title} ] - 类型: {book_type}")
        
        # 根据书籍类型选择处理方式
        if book_type == "多章节":
            novel_content = self._parse_multichapter_novel(content, novel_url, title)
        elif book_type == "内容页内分页":
            novel_content = self._parse_content_pagination_novel(content, novel_url, title)
        else:
            novel_content = self._parse_single_chapter_novel(content, novel_url, title)
        
        print(f'[ {title} ] 完成')
        return novel_content
    
    def _parse_single_chapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """解析单章节小说"""
        # 使用配置的正则提取内容
        chapter_content = self._extract_with_regex(content, self.content_reg)
        
        if not chapter_content:
            raise Exception("无法提取小说内容")
        
        # 执行爬取后处理函数
        processed_content = self._execute_after_crawler_funcs(chapter_content)
        
        return {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': [{
                'chapter_number': 1,
                'title': title,
                'content': processed_content,
                'url': novel_url
            }]
        }
    
    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """解析多章节小说"""
        # 子类必须实现多章节解析逻辑
        raise NotImplementedError("子类必须实现多章节解析逻辑")
    
    def save_to_file(self, novel_content: Dict[str, Any], storage_folder: str) -> str:
        """
        将小说内容保存到文件
        
        Args:
            novel_content: 小说内容字典
            storage_folder: 存储文件夹
            
        Returns:
            文件路径
        """
        # 确保存储目录存在
        os.makedirs(storage_folder, exist_ok=True)
        
        # 生成文件名（使用标题，避免特殊字符）
        title = novel_content.get('title', '未知标题')
        filename = re.sub(r'[<>:"/\\|?*]', '_', title)
        file_path = os.path.join(storage_folder, f"{filename}.txt")
        
        # 如果文件已存在，添加序号
        # counter = 1
        original_path = file_path
        # 如果文件已经存在, 则增书籍网站名称.
        if os.path.exists(file_path):
            file_path = original_path.replace('.txt', f'_{self.novel_site_name}.txt')
        # 如果书籍网站名称的文件也存在, 则返回错误
        if os.path.exists(file_path):
            return 'already_exists'
        # while os.path.exists(file_path):
        #     # 文件已经存在的情况, 应该增加的不是序号, 而是网站名称
        #     file_path = original_path.replace('.txt', f'_{counter}.txt')
        #     counter += 1
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            # 写入标题
            f.write(f"# {title}\n\n")
            
            # 写入章节内容
            chapters = novel_content.get('chapters', [])
            for chapter in chapters:
                chapter_title = chapter.get('title', '未知章节')
                chapter_content = chapter.get('content', '')
                
                f.write(f"## {chapter_title}\n\n")
                f.write(chapter_content)
                f.write("\n\n")
        
        logger.info(f"小说已保存到: {file_path}")
        return file_path
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """从URL中提取小说ID"""
        # 默认实现：从URL中提取文件名部分作为ID
        import os
        filename = os.path.basename(url)
        if '.' in filename:
            filename = filename.rsplit('.', 1)[0]
        return filename or "unknown"
    
    def _parse_content_pagination_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        解析内容页内分页模式的小说（如87nb网站）
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 提取内容页面链接
        content_page_url = self._extract_content_page_url(content)
        if not content_page_url:
            raise Exception("无法找到内容页面链接")
        
        # 构建完整的内容页面URL
        full_content_url = f"{self.base_url}{content_page_url}"
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': []
        }
        
        # 抓取所有章节内容（通过内容页内分页）
        self._get_all_content_pages(full_content_url, novel_content)
        
        return novel_content
    
    def _extract_content_page_url(self, content: str) -> Optional[str]:
        """
        从页面内容中提取内容页面URL
        
        Args:
            content: 页面内容
            
        Returns:
            内容页面URL或None
        """
        # 使用配置的正则表达式提取内容页面链接
        if self.content_page_link_reg:
            for pattern in self.content_page_link_reg:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1)
        
        # 默认模式：查找"开始阅读"链接
        patterns = [
            r'<a[^>]*href="([^"]*ltxs[^"]*)"[^>]*>开始阅读</a>',
            r'<a[^>]*href="([^"]*)"[^>]*>开始阅读</a>',
            r'<a[^>]*href="([^"]*)"[^>]*>阅读全文</a>'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _get_all_content_pages(self, start_url: str, novel_content: Dict[str, Any]) -> None:
        """
        抓取所有内容页面（通过内容页内分页）
        
        Args:
            start_url: 起始内容页面URL
            novel_content: 小说内容字典
        """
        current_url = start_url
        self.chapter_count = 0
        
        while current_url:
            self.chapter_count += 1
            print(f"正在抓取第 {self.chapter_count} 页: {current_url}")
            
            # 获取页面内容
            page_content = self._get_url_content(current_url)
            
            if page_content:
                # 提取章节内容
                chapter_content = self._extract_with_regex(page_content, self.content_reg)
                
                if chapter_content:
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(chapter_content)
                    
                    novel_content['chapters'].append({
                        'chapter_number': self.chapter_count,
                        'title': f"第 {self.chapter_count} 页",
                        'content': processed_content,
                        'url': current_url
                    })
                    print(f"√ 第 {self.chapter_count} 页抓取成功")
                else:
                    print(f"× 第 {self.chapter_count} 页内容提取失败")
            else:
                print(f"× 第 {self.chapter_count} 页抓取失败")
            
            # 获取下一页URL
            next_url = self._get_next_page_url(page_content, current_url)
            current_url = next_url
            
            # 页面间延迟
            time.sleep(1)
    
    def _get_next_page_url(self, content: str, current_url: str) -> Optional[str]:
        """
        获取下一页URL
        
        Args:
            content: 当前页面内容
            current_url: 当前页面URL
            
        Returns:
            下一页URL或None
        """
        # 使用配置的正则表达式提取下一页链接
        if self.next_page_link_reg:
            for pattern in self.next_page_link_reg:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1)
        
        # 默认模式：查找"下一章"或"下一页"链接
        patterns = [
            r'<a[^>]*rel="next"[^>]*href="([^"]*)"[^>]*>',
            r'<a[^>]*href="([^"]*)"[^>]*>下一[章节页]</a>',
            r'<a[^>]*href="([^"]*)"[^>]*>下一[章节页]</a>'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                next_url = match.group(1)
                # 构建完整URL
                if next_url.startswith('/'):
                    return f"{self.base_url}{next_url}"
                elif next_url.startswith('http'):
                    return next_url
                else:
                    # 相对路径处理
                    import os
                    base_dir = os.path.dirname(current_url)
                    return f"{base_dir}/{next_url}"
        
        return None