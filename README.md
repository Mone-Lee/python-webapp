# python-webapp
python学习实践项目，极简博客

#### 环境配置
1. 异步框架 `aiohttp`
2. 前端模板引擎 `jinja2`
3. MySQL的Python异步驱动程序 `aiomysql`  
4. 接收文件内容变化的通知，如果是.py文件，就自动重启wsgiapp.py进程 `watchdog`


#### 项目结构说明
python-webapp/　<-- 根目录  
|
+- backup/　　　　　　　<-- 备份目录  
|  
+- conf/　　　　　　　　　<-- 配置文件  
|  
+- dist/　　　　　　　　　<-- 打包目录  
|  
+- www/　　　　　　　　　<-- Web目录，存放.py文件  
|  |  
|  +- static/　　　　　　　　<-- 存放静态文件  
|  |  
|  +- templates/　　　　　　<-- 存放模板文件  
|  
+- ios/　　　　　　　　　　<-- 存放iOS App工程  

