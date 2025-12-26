FROM python:3.11-slim

RUN set -xe;

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# The following configuration is only needed for Django apps.
ENV DJANGO_ALLOW_ASYNC_UNSAFE="true"
ENV DJANGO_SETTINGS_MODULE=CentralizedLicenseService.settings.prod

# Create a user named app, to run as that instead of root.
RUN groupadd -r app && useradd --create-home --no-log-init -u 1000 -r -g app app && mkdir /app && chown app:app /app
WORKDIR /app

RUN mkdir /app/requirements/

COPY ./docker/app/entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

ADD ./requirements/* /app/requirements/
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements/prod.txt
ADD . /app

USER app

# Add .local/bin to PATH (this is where python bins are put when installed through pip)
ENV PATH="${PATH}:/home/app/.local/bin"

EXPOSE 8000/tcp
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uwsgi", "--ini", "uwsgi.ini"]

