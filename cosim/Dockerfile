FROM python:3.10-slim

RUN apt-get -y update
RUN apt-get -y install git


ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /cosim

RUN mkdir -p /cosim/ip_op

# COPY ./requirements_light.txt /cosim/requirements_light.txt
# RUN pip install -r /cosim/requirements_light.txt
COPY ./requirements_1.txt /cosim/requirements_1.txt
RUN pip install -r /cosim/requirements_1.txt

# Copy submodule `occupant_model`, and upgrade it if necessary
# Note: The submodule should be already cloned before building this docker image
COPY ./src/occupant_model/ /cosim/occupant_model
#RUN pip install /cosim/occupant_model --upgrade

#COPY ./idf_files /cosim/idf_files
# COPY ./idf_files /cosim/idf_files

# Copy ONLY necessary scripts
# We adopt `white-list` here to prevent from copying undesired contents
# COPY ./cosim/src/CoSimCore.py /cosim/CoSimCore.py
# COPY ./cosim/src/CoSimDict.py /cosim/CoSimDict.py
# COPY ./cosim/src/CoSimUtils.py /cosim/CoSimUtils.py
# COPY ./cosim/src/CoSimMain.py /cosim/CoSimMain.py
# COPY ./cosim/src/thermostat.py /cosim/thermostat.py
# Copy all except the directories in the .dockerignore file
COPY . /cosim/ 

# RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /cosim
# USER appuser

CMD ["python", "src/CoSimMain.py"]
