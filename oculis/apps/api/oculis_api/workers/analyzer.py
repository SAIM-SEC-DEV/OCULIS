from rq import Worker

from oculis_api.services.queue import get_analysis_queue

if __name__ == "__main__":
    Worker([get_analysis_queue()], name="oculis-analyzer").work()
