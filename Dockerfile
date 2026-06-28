FROM php:8.2-apache

# 安裝資料庫連線套件
RUN docker-php-ext-install pdo pdo_mysql

# 啟用 Apache 路由重寫 (對應 .htaccess) 與 Headers
RUN a2enmod rewrite headers

WORKDIR /var/www/html

COPY . /var/www/html/

EXPOSE 80