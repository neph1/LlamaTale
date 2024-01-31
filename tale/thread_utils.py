import threading

def do_in_background(lambda_task: callable):
    result_event = threading.Event()

    task_thread = threading.Thread(target=lambda_task, args=(result_event,))
    result_event.set()
    task_thread.start()
    task_thread.join()

    return result_event.is_set()