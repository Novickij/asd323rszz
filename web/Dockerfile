FROM nginx:alpine

COPY redirect.html /usr/share/nginx/html/redirect.html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]