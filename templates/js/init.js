// 数据源为 SQLite：先异步加载，加载完成后再进入默认虾剧页（★ 剧本先行）
(async () => {
  if(!IS_SERVER){
    const c = $("content");
    if(c) c.innerHTML = '<div style="padding:60px 20px;text-align:center;color:var(--mut);font-size:13px;line-height:2">数据已迁移到 SQLite 数据库<br>请双击「启动项目台.bat」以服务模式打开（浏览器 http://127.0.0.1:8320）</div>';
    return;
  }
  const ok = await loadProjectFromDb();
  if(ok){ renderSection("xiaju"); initTaskbar(); }
  else {
    const c = $("content");
    if(c) c.innerHTML = '<div style="padding:60px 20px;text-align:center;color:#b91c1c;font-size:13px">数据加载失败：数据库为空或服务异常<br>请运行 POST /db/migrate 迁移数据后刷新</div>';
    initTaskbar();
  }
})();


