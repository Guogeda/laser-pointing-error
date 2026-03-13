@echo off
cd /d "c:\Users\17251\Desktop\激光指向误差计算"
echo 检查变更...
git status
echo.
echo 暂存已跟踪文件...
git add -u
echo.
echo 提交变更...
git commit -m "自动提交变更"
echo.
echo 推送到GitHub...
git push
echo.
echo 完成！
pause
