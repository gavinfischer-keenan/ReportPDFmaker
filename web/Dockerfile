FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html LICENSE.txt /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/
COPY js/ /usr/share/nginx/html/js/
COPY vendor/ /usr/share/nginx/html/vendor/
COPY assets/ /usr/share/nginx/html/assets/
EXPOSE 80
