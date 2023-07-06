FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /cosim

COPY ./cosim/requirements_light.txt /cosim/requirements_light.txt
RUN pip install -r /cosim/requirements_light.txt

# Copy submodule `occupant_model`, and upgrade it if necessary
# Note: The submodule should be already cloned before building this docker image
COPY ./occupant_model /cosim/occupant_model
#RUN pip install /cosim/occupant_model --upgrade

#COPY ./idf_files /cosim/idf_files
COPY ./idf_files /cosim/idf_files

# Copy ONLY necessary scripts
# We adopt `white-list` here to prevent from copying undesired contents
COPY ./CoSimCore.py /cosim/CoSimCore.py
COPY ./CoSimDict.py /cosim/CoSimDict.py
COPY ./CoSimUtils.py /cosim/CoSimUtils.py
COPY ./CoSimMainCMD.py /cosim/CoSimMainCMD.py
COPY ./thermostat.py /cosim/thermostat.py

# RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /cosim
# USER appuser

CMD ["python", "CoSimMainCMD.py"]
