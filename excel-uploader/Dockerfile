# Usamos una imagen base de Node.js
FROM node:16

# Establecer el directorio de trabajo en el contenedor
WORKDIR /usr/src/app

# Copiar package.json y package-lock.json (si existe)
COPY excel-uploader/package*.json ./

# Instalar dependencias
RUN npm install

# Copiar archivos y carpetas específicos del proyecto
COPY excel-uploader/src ./src


# Instalar Angular CLI globalmente
RUN npm install -g @angular/cli@15.2.0


# Comando para iniciar la aplicación en modo desarrollo
CMD ["ng", "serve", "--host", "0.0.0.0", "--port", "4200"]