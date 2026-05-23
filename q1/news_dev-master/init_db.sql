-- =============================================
-- 融媒体新闻采编发布系统 - 数据库初始化
-- 区域融媒体中心 © 2024
-- =============================================

CREATE DATABASE IF NOT EXISTS baixiu DEFAULT CHARSET utf8mb4;
USE baixiu;

-- ----------------------------
-- 用户表 (密码明文存储)
-- ----------------------------
DROP TABLE IF EXISTS users;
CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(100) NOT NULL,
  password VARCHAR(64) NOT NULL,
  avatar VARCHAR(500) DEFAULT '/baixiu/static/assets/img/default.png',
  nickname VARCHAR(50) DEFAULT NULL,
  slug VARCHAR(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------
-- 分类目录表
-- ----------------------------
DROP TABLE IF EXISTS categories;
CREATE TABLE categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  slug VARCHAR(100) NOT NULL,
  name VARCHAR(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------
-- 文章表
-- ----------------------------
DROP TABLE IF EXISTS posts;
CREATE TABLE posts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(200) NOT NULL,
  content TEXT,
  user_id INT NOT NULL,
  category_id INT NOT NULL,
  slug VARCHAR(200) DEFAULT NULL,
  feature VARCHAR(500) DEFAULT NULL,
  created DATETIME DEFAULT CURRENT_TIMESTAMP,
  status ENUM('published','drafted','trashed') DEFAULT 'drafted'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------
-- 评论表
-- ----------------------------
DROP TABLE IF EXISTS comments;
CREATE TABLE comments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  author VARCHAR(100) NOT NULL,
  content TEXT NOT NULL,
  post_id INT NOT NULL,
  created DATETIME DEFAULT CURRENT_TIMESTAMP,
  status ENUM('held','approved','rejected') DEFAULT 'held'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------
-- 设置表
-- ----------------------------
DROP TABLE IF EXISTS options;
CREATE TABLE options (
  id INT AUTO_INCREMENT PRIMARY KEY,
  option_name VARCHAR(100) NOT NULL,
  option_value TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =============================================
-- 预设数据
-- =============================================

-- 管理员账号
INSERT INTO users (id, email, password, avatar, nickname, slug) VALUES
(1, 'admin', 'Media@News2024', '/baixiu/static/assets/img/default.png', '系统管理员', 'admin'),
(2, 'editor', 'Edit0r@2024', '/baixiu/static/assets/img/default.png', '内容编辑', 'editor');

-- 新闻分类 (广电融媒体主题)
INSERT INTO categories (id, slug, name) VALUES
(1, 'zhengce-jiedu', '政策解读'),
(2, 'minsheng-xinwen', '民生新闻'),
(3, 'huodong-baodao', '活动报道'),
(4, 'xuanchuan-tongzhi', '宣传通知');

-- 示例新闻文章
INSERT INTO posts (id, title, content, user_id, category_id, slug, status, created) VALUES
(1, '关于印发2024年度融媒体中心工作要点的通知',
 '<p>各相关部门：</p><p>为深入贯彻落实党中央关于媒体融合发展的决策部署，加快推进区域融媒体中心建设，现将2024年度工作要点通知如下：</p><p>一、深化内容生产改革，提升新闻舆论传播力、引导力、影响力、公信力。</p><p>二、推进技术平台升级，实现"一次采集、多种生成、多元传播"的全媒体生产流程。</p><p>三、加强人才队伍建设，培养复合型融媒体人才。</p>',
 1, 4, '2024-work-notice', 'published', '2024-03-15 09:00:00'),

(2, '我市全面推进县级融媒体中心建设成效显著',
 '<p>近日，我市召开县级融媒体中心建设现场推进会。会议指出，自去年启动县级融媒体中心建设以来，各区县积极整合广播、电视、报纸、新媒体等资源，初步建成了一批具有区域特色的融媒体平台。</p><p>与会代表参观了青山县融媒体中心，该中心自主研发的"融媒体新闻采编发布系统"已投入使用，实现了新闻采编流程的数字化管理。</p>',
 2, 1, 'rongmeiti-construction', 'published', '2024-03-14 10:30:00'),

(3, '社区文化节"百姓舞台"系列活动圆满落幕',
 '<p>为期一周的"百姓舞台"社区文化节在市民广场圆满落下帷幕。本次活动由区委宣传部、区融媒体中心联合主办，共吸引了超过5000名市民参与。</p><p>活动期间，区融媒体中心全程进行了网络直播，累计观看人次超过10万，有效提升了区域文化活动的传播力和影响力。</p>',
 2, 3, 'community-culture-festival', 'published', '2024-03-13 15:00:00'),

(4, '关于做好2024年汛期广播电视安全播出工作的通知',
 '<p>各播出机构：</p><p>汛期将至，为确保广播电视安全播出，保障人民群众及时收听收看广播电视节目，现将有关事项通知如下：</p><p>一、严格落实安全播出主体责任，完善应急预案。</p><p>二、加强播出机房、传输线路、供电系统的巡检维护。</p><p>三、实行24小时值班制度，遇有突发情况及时上报。</p>',
 1, 4, 'flood-season-notice', 'published', '2024-03-12 08:00:00'),

(5, '数字电视惠民工程惠及10万户农村家庭',
 '<p>记者从市文广旅局获悉，我市数字电视惠民工程进展顺利，截至目前已惠及10万余户农村家庭。</p><p>该工程通过政府补贴的方式，为农村居民免费安装数字电视机顶盒，提供不少于70套数字电视节目。下一步，将继续扩大覆盖范围，让更多群众享受到高质量的广播电视公共服务。</p>',
 2, 2, 'digital-tv-project', 'published', '2024-03-10 14:00:00'),

(6, '2024年春节联欢晚会录制工作圆满完成',
 '<p>经过两个月的精心筹备，区域融媒体中心2024年春节联欢晚会于近日完成录制工作。晚会以"凝心聚力·共创未来"为主题，汇集了歌舞、戏曲、小品、相声等各类节目。</p><p>节目将于除夕夜在新闻综合频道首播，同时通过融媒体平台同步网络直播。</p>',
 2, 3, 'spring-festival-gala', 'published', '2024-02-01 16:00:00');

-- 示例评论
INSERT INTO comments (id, author, content, post_id, status, created) VALUES
(1, '基层广电人', '支持融媒体建设！希望系统越来越好用', 2, 'approved', '2024-03-14 11:30:00'),
(2, '市民代表', '社区文化活动很精彩，融媒体直播画质清晰流畅', 3, 'approved', '2024-03-13 16:20:00'),
(3, '乡镇站长', '惠民工程真实惠，老百姓都说好', 5, 'approved', '2024-03-10 15:00:00'),
(4, '热心观众', '期待今年的春晚节目！', 6, 'held', '2024-02-02 09:00:00');

-- 站点设置
INSERT INTO options (option_name, option_value) VALUES
('site_name', '融媒体新闻采编发布系统'),
('site_description', '区域融媒体中心官方新闻发布平台'),
('site_keywords', '融媒体,新闻,广电,采编,发布'),
('site_logo', '/baixiu/static/assets/img/logo.png');
