FROM docker.io/smallstep/step-cli:latest

USER root
# Copy in our init script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

User step
ENTRYPOINT ["entrypoint.sh"]
