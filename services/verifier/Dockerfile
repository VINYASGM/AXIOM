FROM python:3.11-slim

WORKDIR /app

RUN pip install grpcio grpcio-tools protobuf

COPY proto/verifier.proto /app/proto/verifier.proto
COPY verifier_stub.py /app/main.py

# Generate gRPC code
RUN python -m grpc_tools.protoc -I/app/proto --python_out=. --grpc_python_out=. /app/proto/verifier.proto

EXPOSE 50051

CMD ["python", "main.py"]
