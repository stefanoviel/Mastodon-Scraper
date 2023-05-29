# loading and saving queues 
import asyncio

class MangageQueue: 

    def __init__(self) -> None:
        pass

    async def load_queue(self, path): 
        queue = asyncio.Queue()
        with open(path) as file: 
            for line in file.readlines(): 
                await queue.put(tuple(line.split(',')))
        return queue
    
    async def save_queue(self, queue, path): 
        with open(path) as file: 
            while queue.qsize() > 0: 
                file.write(await queue.get())
