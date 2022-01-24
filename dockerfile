FROM --platform=linux/x86-64 python:3.8
RUN mkdir /expocapital_bot
COPY transaction_notifier.py /expocapital_bot
COPY state.py /expocapital_bot
RUN pip install requests
RUN pip install schedule
CMD ["python", "/expocapital_bot/transaction_notifier.py"]