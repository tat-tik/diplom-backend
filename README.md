1. Подключаемся к серверу
  ssh root@IP,
    где IP - где IP - это ip-адрес вашего сервера и вводим пароль из письма

2. Создаем отдельного пользователя <ИМЯ ПОЛЬЗОВАТЕЛЯ> и назначем его администратором:
adduser <ИМЯ ПОЛЬЗОВАТЕЛЯ>
usermod <ИМЯ ПОЛЬЗОВАТЕЛЯ> -aG sudo
su <ИМЯ ПОЛЬЗОВАТЕЛЯ>
Возвращаемся в домашнюю директорию: cd ~
 
3. Обновляем пакетный менеджер sudo apt update

4. Устанавливаем зависимости sudo apt install python3-venv python3-pip postgresql nginx

5. Скачиваем backend проект 
git clone https://github.com/tat-tik/diplom-backend.git

6. Создаем отдельного пользователя postgresql
   sudo su postgres
ALTER USER postgres WITH PASSWORD 'postgres';
CREATE DATABASE Diplom_my_cloud;

7. Добавляем настройки в settings.py:
DATABASE:{ 
    NAME: 'Diplom_my_cloud',
    HOST: 'localhost',
    PORT: '5432',
    USER: 'postgres',
    PASSWORD: 'postgres',
}
6. Переходим в папку backstore и устанавливаем виртуальное окружение:
   python3 -m venv env
   Активируем виртуальное окружение:
   source env/bin/activate

5. Устанавливаем все зависимости из файла requirements.txt
    pip install -r requirements.txt

6. Делаем миграции:
    python manage.py migrate

7. Создаем файл настроек gunicorn:
sudo nano /etc/systemd/system/gunicorn.service

[Unit]
Description=gunicorn service After=network.target

[Service]
User=tatik
Group=www-data
WorkingDirectory=/home/tatik/diplom-backend
ExecStart=/home/tatik/diplom-backend/env/bin/gunicorn \
         --access-logfile - \
         --workers 3 \
         --bind unix:/home/tatik/diplom-backend/backstore/gunicorn.sock \
         backstore.wsgi:application

[Install]
WantedBy=multi-user.target

8. Запускаем gunicorn:

    sudo systemctl start gunicorn
    sudo systemctl enable gunicorn
Проверяем статус (должен быть Active):
sudo systemctl start gunicorn

9. Настраиваем файл конфигурации сервера:
sudo nano /etc/nginx/sites-available/backstore

server {
   listen 80;
   server_name 130.49.149.98;

 location = /favicon.ico {
      access_log off;
      log_not_found off;
   }


   location /static/ {
      alias /home/tatik/diplom-backend/staticfiles/;
   }

   location /admin/ {
        include proxy_params;
        proxy_pass http://unix:/home/tatik/diplom-backend/backstore/gunicorn.sock;
    }

   location /api/ {
      include proxy_params;
      proxy_pass http://unix:/home/tatik/diplom-backend/backstore/gunicorn.sock;
      }


10. Создаем ссылку sudo ln -s /etc/nginx/sites-availeble/backstore etc/nginx/sites-enable

11. Перезапускаем nginx
sudo systemctl reload nginx

12. В файле настроек /etc/nginx/nginx.conf, необхожимо отключить проверку размера тела запроса с клиента, для возможности отправки на сервер больших файлов. Добавьте в конец блока http {} файла конфигурации строчку: client_max_body_size 0;

13. Разрешите полные права для Nginx: sudo ufw allow 'Nginx Full'

14. Чтобы не было конфликтов удалим default - стандартную конфигурацию Nginx, которая создаётся при установке: 
    sudo rm /etc/nginx/sites-enabled/default

15. Для обновления рабочей конфигурации перезапустите веб-сервер Nginx:
    sudo systemctl reload nginx

16. Перейдите к разворачиванию frontend на сервере. 
1Инструкция по разворачиванию находится в файле READEME.md в корне проекта frontend.