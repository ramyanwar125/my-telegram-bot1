# استخدام نسخة PHP مع سيرفر Apache جاهز
FROM php:8.1-apache

# تغيير منفذ Apache ليتوافق مع ريندر
RUN sed -i 's/80/${PORT}/g' /etc/apache2/sites-available/000-default.conf /etc/apache2/ports.conf

# نسخ ملفات البوت إلى السيرفر
COPY . /var/www/html/

# إعطاء صلاحيات الكتابة للمجلدات (لأن بوتك ينشئ ملفات)
RUN chmod -R 777 /var/www/html/

# تشغيل السيرفر
CMD ["apache2-foreground"]
