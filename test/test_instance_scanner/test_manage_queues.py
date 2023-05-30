import unittest
import asyncio
import aiohttp
import mock


from src.instances_scanner.manage_queues import MangageQueue


class TestInstanceScanner(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.manage_queueu = MangageQueue()

    @mock.patch("builtins.open", new_callable=mock.mock_open, read_data="data")
    async def test_right_file_opened(self, mock_file):
        file_path = 'file/path'
        await self.manage_queueu.load_queue(file_path)
        mock_file.assert_called_with(file_path)

    @mock.patch("builtins.open", new_callable=mock.mock_open, read_data=''.join(str(line) + '\n' for line in range(50)))
    async def test_number_of_line_read(self, mock_file):
        file_path = 'file/path'
        queue = await self.manage_queueu.load_queue(file_path)
        self.assertEqual(50, queue.qsize())

    @mock.patch("builtins.open", new_callable=mock.mock_open, read_data=''.join(str(line) + ',' + 'second' + '\n' for line in range(50)))
    async def test_line_separated(self, mock_file):
        file_path = 'file/path'
        queue = await self.manage_queueu.load_queue(file_path)
        for i in range(50): 
            first, second = await queue.get()
            self.assertEqual(first, str(i))
            self.assertEqual(second, 'second\n')
    
    @mock.patch("builtins.open", new_callable=mock.mock_open)
    async def test_right_file_opened_to_save(self, mock_file):
        file_path = 'file/path'
        queue = asyncio.Queue()
        await self.manage_queueu.save_queue(queue,file_path)
        mock_file.assert_called_with(file_path)

    
    @mock.patch("builtins.open", new_callable=mock.mock_open)
    async def test_number_of_line_written(self, mock_file):
        queue = asyncio.Queue()
        file_path = 'file/path'
        for i in range(50): 
            await queue.put((str(i), 'second'))
        await self.manage_queueu.save_queue(queue, file_path)
        for i in range(50): 
            mock_file().write.assert_any_call((str(i), 'second'))

        
            
if __name__ == '__main__':
    unittest.main()
