import asyncio
import aiohttp
import logging
from manageDB import ManageDB

class InstanceScanner: 

    def __init__(self, instance_name:str, id_queue: asyncio.Queue,  sort_queue: asyncio.Queue ) -> None:
        self.instance_name = instance_name
        self.id_queue = id_queue
        self.follower_queue = asyncio.Queue()
        self.following_queue = asyncio.Queue()
        self.sort_queue = sort_queue
        self.manageDB = ManageDB('users')

        self.manageDB.reset_collections()  # TODO: remove
        
        logging.basicConfig(level=logging.DEBUG)

    async def get_id_from_url(self, session, username) -> None:
        "get id of users, put them in following follower queue and save user info"
        url = 'https://{}/api/v2/search/?q={}'.format(self.instance_name, username) 

        async with session.get(url, timeout=5) as response:
            res = await response.json()
        
        account_id = res['accounts'][0]['id']
        await self.follower_queue.put('https://{}/api/v1/accounts/{}/followers/'.format(self.instance_name, account_id))
        await self.following_queue.put('https://{}/api/v1/accounts/{}/following/'.format(self.instance_name, account_id))

        self.save_users(res)



    async def get_following_followers(self, session: aiohttp.ClientSession, url: str) -> None:
        # get element from following follower queue and query some pages save results in sort queue

        params = {'limit': 80}
        async with session.get(url, params = params, timeout=5) as response:
            res = await response.json()

            if 'next' in response.links.keys():
                new_url = str(response.links['next']['url'])
                logging.debug('adding {} to queue '.format(new_url))
                              
                if 'followers' in new_url: 
                    await self.follower_queue.put(new_url)
                elif 'following' in new_url: 
                    await self.following_queue.put(new_url)

        await self.save_users(res)

        # TODO: user of this instance go to following followers queue (we already have the id), of other instances go to sorter
            

    async def save_users(self, user_list:list[dict]): 
        posts = []
        for r in user_list: 
            print(r["url"])
            r["_id"] = r["url"].replace("https://", '')
            r["instance"] = self.instance_name
            posts.append(r)

        
        print('saving results len {}'.format(len(posts)))
        self.manageDB.insert_many_to_archive(posts)

    async def request_id(self, task: list, session: aiohttp.ClientSession) -> None: 
        for completed_requests in range(240): 
            if not self.id_queue.empty(): 
                name = await self.id_queue.get()
                tasks.append(asyncio.create_task(self.get_id_from_url(session, name)))
            else: 
                n_request += round((240 - completed_requests)/2)  # use remaining requests for followers and following
                break

            logging.debug('follower queue len {}'.format(self.follower_queue.qsize()))



    async def request_manager(self): 
        # execute 280 requests 240 for ids 40 for followers 
        # dynamically set parameters ??? 

        # await self.follower_queue.put('https://mastodon.social/api/v1/accounts/1/followers/')
        # await self.follower_queue.put('https://mastodon.social/api/v1/accounts/1/following/')

        name_list = ['@Happ',
                    '@firstfemalepope',
                    '@chetalmario',
                    '@Ivy_gay',
                    '@mdv01',
                    '@gakoid',
                    '@sergeidiot',
                    '@yogeshsabne',
                    '@p54',
                    '@Murray_felicia',
                    '@leakycolddrink',
                    '@Tivolay23',
                    '@KemalWorld',
                    '@marioandweegee3',
                    '@c88tm',
                    '@hamza102',
                    '@JoeBell',
                    '@ElNosferatu',
                    '@gretchgoes',
                    '@amazing_psyconix',
                    '@pa_james',
                    '@LilyOwen',
                    '@janosp',
                    '@brendagray',
                    '@RHeuke',
                    '@NilsToAn',
                    '@Vinhgiap',
                    '@chironomia',
                    '@fdromeen',
                    '@waseem2004',
                    '@amazing_ABB',
                    '@arindamhronline',
                    '@Purple_Sky',
                    '@eiji24g',
                    '@OneEyedWilly',
                    '@carhireinahmedabad',
                    '@chillmomster',
                    '@liban',
                    '@theinterline',
                    '@discgolfphil',
                    '@Fictionauthor',
                    '@frederiknoom',
                    '@su6573921',
                    '@susannaOV',
                    '@upnhiicut2099258',
                    '@tofuwater',
                    '@qwfqwer1tf',
                    '@rodhilton',
                    '@davidpierce',
                    '@arstechnica',
                    '@nilaypatel',
                    '@nitashatiku',
                    '@thedextriarchy',
                    '@ianmcque',
                    '@rhipratchett',
                    '@ZachWeinersmith',
                    '@MrLovenstein',
                    '@mastodonusercount',
                    '@tiffanycli',
                    '@triketora',
                    '@sandofsky',
                    '@tenderlove',
                    '@lindsayellis',
                    '@tvler',
                    '@williamgunn',
                    '@davidslifka',
                    '@jonasdowney',
                    '@RebeccaSlatkin',
                    '@xeraa',
                    '@12tonevideos',
                    '@inganomads',
                    '@oatmeal',
                    '@antirez',
                    '@b3ll',
                    '@dporiua',
                    '@chockenberry',
                    '@gruber',
                    '@MarkRuffalo',
                    '@JxckS',
                    '@Prime',
                    '@fastmail',
                    '@Popehat',
                    '@AbandonedAmerica',
                    '@GreatDismal',
                    '@chendo',
                    '@gael',
                    '@Phico',
                    '@neilhimself',
                    '@taylorlorenz',
                    '@Sarahp',
                    '@NotFrauKadse',
                    '@a2_4am',
                    '@mika_',
                    '@alexoak',
                    '@danielgamage',
                    '@tttylee',
                    '@sskylar',
                    '@biscuitcats',
                    '@sundogplanets',
                    '@ummjackson',
                    '@whyvinca',
                    '@nezha79888888',
                    '@vootours',
                    '@dariod',
                    '@lauren2',
                    '@funny_clowny_goofy',
                    '@dcurtisv',
                    '@mr9618033',
                    '@justyntemme',
                    '@quantboy',
                    '@decide4kamal',
                    '@HighDef',
                    '@jujh',
                    '@mrDarcyMurphy',
                    '@rustyhaider',
                    '@HadisNazari',
                    '@Dunkadevloawsharverselwaviii',
                    '@pymode_dev',
                    '@drsfirst',
                    '@handsomemags',
                    '@noamcohen',
                    '@msteimel3',
                    '@carfixdubai42',
                    '@Divinewealth',
                    '@jenniferlipa',
                    '@Ross_Taphari',
                    '@FeuerkopfHenryk',
                    '@caneuroinst',
                    '@axmaw98',
                    '@Gugvghy',
                    '@cacvinst',
                    '@stephaniejgolden',
                    '@_rjmorgan',
                    '@nonlocal',
                    '@Sierra_117',
                    '@jordan12',
                    '@un1crom',
                    '@notFlorian',
                    '@Dsop',
                    '@ambler',
                    '@christopheduc',
                    '@a_flatters',
                    '@Stephanie00',
                    '@Tikur',
                    '@neptoon',
                    '@PeakeABoo',
                    '@lebjoernski',
                    '@mashhudusman',
                    '@stuhijk',
                    '@ghalldev',
                    '@aldybc',
                    '@uditmehra631',
                    '@ritika13',
                    '@Dunkadevloawsharverselwavii',
                    '@glynmoody',
                    '@PCMag',
                    '@aTastyT0ast',
                    '@bigzaphod',
                    '@pixelfed',
                    '@andybalaam',
                    '@batterpunts',
                    '@scruss',
                    '@aguasmenores',
                    '@sybren',
                    '@kornel',
                    '@DavidBlue',
                    '@tommeypinkiemonkey',
                    '@noybeu',
                    '@jeffgerstmann',
                    '@lickability',
                    '@matthewbischoff',
                    '@mellifluousbox',
                    '@gcluley',
                    '@lrvick',
                    '@Edent',
                    '@jk',
                    '@jjb',
                    '@Select',
                    '@frazerb',
                    '@unijena']
        
        for i in name_list: 
            await self.id_queue.put(i)

        async with aiohttp.ClientSession(trust_env=True) as session:
            while not self.follower_queue.empty() or not self.id_queue.empty or not self.following_queue.empty(): 
                
                tasks = []

                first = False
                n_request = 20 # 20*2 = 40
                
               

                # while n_request > 0:  
                #     logging.debug(n_request)
                #     if not self.follower_queue.empty(): 
                #         url = await self.follower_queue.get()
                #         tasks.append(asyncio.create_task(self.get_following_followers(session, url)))
                #     else: 
                #         n_request += 1 # one more query
                #         first = True

                #     if not self.following_queue.empty(): 
                #         url = await self.following_queue.get()
                #         tasks.append(asyncio.create_task(self.get_following_followers(session, url)))
                #     else: 
                #         n_request += 1
                #         if first: 
                #             break

                #     n_request -= 2
                #     await asyncio.sleep(2)




                await asyncio.gather(*tasks)

                logging.debug('done')

                # await asyncio.sleep(310)


async def test(): 

    instanceScanner = InstanceScanner('mastodon.social', asyncio.Queue(), asyncio.Queue())
    await instanceScanner.request_manager()

if __name__ == "__main__": 

    asyncio.run(test())
