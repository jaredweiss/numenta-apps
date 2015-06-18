FROM <registry>/nta.utils
ADD . /opt/numenta/nta.utils/
WORKDIR /opt/numenta/nta.utils
CMD ./run.py --host=${RABBITMQ_HOST} --user=${RABBITMQ_USER} --password=${RABBITMQ_PASSWD}