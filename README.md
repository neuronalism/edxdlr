# edX Mini Downloader

一个 edX 课程下载器，改自 edx-dl 项目 (https://github.com/coursera-dl/edx-dl)。

看起来原来的项目已经无人维护了，按照 edX 官方提供的 API 修改了原来的代码。由于本人比较菜、没怎么写过 python 代码，也顺便删掉了一些看得不顺眼的功能（具体见下）。

## 使用方法

首先，你要有一个 edX 的账号，并且你要 enroll 进你想下载的课程里 **（目前只能是 Started 课程，不能是 Archived）** 。

然后，在命令行里输入 `python edxdlr.py `，后面跟上命令。

**两个常用命令：**

- 查看所有课程 `python edxdlr.py -u USERNAME -p PASSWORD --list-courses`
- 下载某一门课  `python edxdlr.py -u USERNAME -p PASSWORD COURSEID`(COURSEID 见下)

其它命令可 `python edxdlr.py --help` 来查看。

**COURSEID 即课程 ID**。举个例子，如果你的课程链接是 https://learning.edx.org/course/course-v1:CornellX_UQx+BIOEE101x+2T2021/home，那么课程 ID 就是中间的那一串 course-v1:CornellX_UQx+BIOEE101x+2T2021。

### 使用限制

**目前只支持新链接格式，即 learning.edx.org 开头的课程。老课程链接，即链接以 courses.edx.org 开头，暂时不支持下载。**

### 安装要求

需要 python 3.6 或更高环境，以及下列依赖包（可用 pip 安装）：

- beautifulsoup4
- html5lib
- six
- requests

把几个文件下载到同一个文件夹，cmd 里能访问到就可以用。

### 与原 edx-dl 的不同之处

- 修改：选择课程时，不需要输入完整课程路径，只要输入课程ID即可。
- 增加：网页下载功能。原来的 edx-dl 只下载视频、不下载网页，现在都会下载并放在文件夹里。**目前图片下载还有问题**，我想想要怎么解决（也可能不解决了
- 移除：多线程下载，也就是现在所有的都是 `–sequential` 方式下载（因为我没有debug 环境，只能改一点程序执行一次看看对不对。不过这样下载有点慢就是了）
- 移除：各自我看不懂的 filter 功能（
- 移除：从 YouTube 下载视频的功能（本来 edX 不少视频都在 CDN 上有，干嘛要多个 youtube-dl 的依赖呢）

## 常见问题

1. 这程序会不会记录我的密码？

   会，但只在运行时候记住。下次运行还要再输入一次。（你不给也没法登录啊）

2. 访问不了 edx？

   这我帮不了你。

3. 有课程下不了？

   在浏览器里登录账号后，在 dashboard 里确认你的课程是 Started（不是Archived），且符合上面说的课程链接格式。如果还是下载不了，发个 issue，带上课程链接和报错信息我看看。

4. 其它程序崩溃问题？

   任何出错，都先看看浏览器里自己的账号能不能登录、dashboard 能不能看到、课程链接都对不对。如果都符合条件，请发个 issue，带上课程链接和报错信息我看看。

## 免责声明

本程序仅提供一种非浏览器方式访问 edX 网站的方法。使用者在使用本程序时需要满足 edX 的使用条款 ([Terms of Service | edX](https://www.edx.org/edx-terms-service))，限使用者本人出于个人学习目的使用。任何使用者的不当操作与本程序无关。