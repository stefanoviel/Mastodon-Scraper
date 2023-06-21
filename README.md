## How to run

Activate mongoDB

run the following command to scrape the instances

```
python -m src.scan_instances
```

run the following command to scrape the users

```
python -m src.user_sorter
```

## Introduction - what is mastodon? 

Mastodon is a decentralized and open-source social networking platform. It operates on a model known as "federated social networking," where multiple independent servers, called "instances," connect with each other to form a network of interconnected communities. Each instance represents a distinct community with its own rules and moderation policies.

Users on Mastodon can create accounts on any instance of their choice or even set up their own instance. Within an instance, users can post messages (referred to as "toots") that can include text, images, videos, and links. These toots can be shared, liked, and commented on by other users from any instance. A user can follow users from the same or other instances. 

While instances can connect with each other through a federation process, where they exchange information and communicate, <span style="text-decoration:underline;">it is not guaranteed that every instance will be directly connected to all other instances in the network</span>. Therefore, while you can follow and interact with users from different instances in the Mastodon network, the reach and visibility of any particular instance may be limited to its own users and those instances directly connected to it through federation.


## The task

The aim of the project is to create two graphs: one about the instances, their information and all the connection among them (each instance isn’t necessarily aware of the existence of all the other instances) and another one about the users, their information and the connection among them (followers, following, number of toots posted ecc. ecc.) 


## APIs

The software that needs to be install on a server in order to create an instance offers some publicly available APIs. These APIs can be accessed by anyone. I guess they’re necessary for the exchange of information among instances (couldn’t find any information about this). 

Each instance allows for at most 300 requests every five minutes. 

The useful for our task are the following: 

**GET name of the instance + /api/v1/instance**

returns a json with the information of the instance

Example [https://mastodon.social/api/v1/instance](https://mastodon.social/api/v1/instance) 

relevant returned parameters: 



* uri: name of the instance
* user_count: number of users registered on the instance
* status_count: number of toots posted on the instance
* domain_count: number of domains discovered by the instance (i.e. the number of peers)
* rules: need to be accepted before registering in the instance

A full list of these parameters and their meaning can be found here:  [https://docs.joinmastodon.org/entities/V1_Instance/](https://docs.joinmastodon.org/entities/V1_Instance/) 

**GET name of the instance + /api/v1/instance/peers**

return a list of all the known instances 

Example [https://mastodon.social/api/v1/instance/peers](https://mastodon.social/api/v1/instance/peers) 

returns ["smgle.com","mstdn.nielniel.net","testdon00001.mamemo.online","lazybear.io", …]

**GET name of the instance + /api/v2/search/?q={username}**

returns a list of users who match the given username (even if it’s just in the displayed name)

Example [https://mastodon.social/api/v2/search/?q=Gargron](https://mastodon.social/api/v2/search/?q=Gargron)

relevant returned parameters: 



* numerical id: each instance assigns a numerical id to all the known users (the id for the same users will be changed between different instances). This numerical id is necessary in order to use the following API. 
* followers_count: number of followers
* following_count: number of users who follows this account
* status_count: number of toots (posts) of this users
* bot: true/false depending if the account is a bot
* created_at: date of creation of the account

**GET name of instance + /api/v1/accounts/{numerical id}/followers/**

returns a list of dictionaries each of which contains the information of the followers of this user. The information are the same as the one returned by **/api/v2/search/?q={username}**, so for the followers who belong to the same instance of the followed account we can directly used their numerical id to find their respective followers; for the followers who don’t belong to the same instance of the followed account we’ll have to use **/api/v2/search/?q={username} **to get their id on their native instance. 

In the header we can include the parameter _limit_ (at most 80) which will be the number of followers or following returned. 

Only a limited number of followers can be obtained with each request, so pagination has been implemented in order to iteratively acquire all the followers of a certain user. In the link header under “next” and then “url” we can obtain the link to the next page of followers. In python: 


```
next_url = response.links['next']['url']
```


Example: [https://mastodon.social/api/v1/accounts/1/followers/](https://mastodon.social/api/v1/accounts/1/followers/)

**GET name of instance + /api/v1/accounts/{numerical id}/followers/**

Same as above: gets the list of user (and their information) followed by the user whit numerical id. 


## Code for scraping instances

[scan_instances.py]

Due to its decentralized nature there is no available list of all the existing instances as they’re continuously being created and taken down. So, the only way to gather all the instances, their information and the connections among them is to start from one instance, fetch its information, then ask for its peers and recursively repeat the process until there are no new instances to scrape. In other words we’ll do a breadth first search (BFS) on the graph of all instances.

The starting instance will be mastodon.social, it is the most popular one and it was created by the founder of the mastodon.



<p id="gdcalert1" ><span style="color: red; font-weight: bold">>>>>>  gd2md-html alert: inline image link here (to images/image1.png). Store image on your image server and adjust path/filename/extension if necessary. </span><br>(<a href="#">Back to top</a>)(<a href="#gdcalert2">Next alert</a>)<br><span style="color: red; font-weight: bold">>>>>> </span></p>



As we can see from the schema the code is composed by two parts: 



* One loop to scrape the instance peers
* Another loop to scrape the instance info

These two have a mutual producer-consumer relation. The peers scraper gets the instances (and their information) from the peers queue and then requests the peers of the instance from the API. These peers are then added to the instance queue, so every element in the instance queue will just be the name of the instance. 

The info scraper gets the name of the instances from the instance queue, it requests the information of that specific instance from the API and adds the results to the peers queue. So, on the peers queue we will have the instance along with all its relevant information. 

Both the info and peers scraper saves the information they have obtained in mongoDB. The info scraper creates the JSON in the database, while the peers scraper adds the peers to the previously created JSON. 

Every n iteration (this parameter can be set from the code) the queues are saved in a text file. In order to not use too much memory the peer queue (bigger in memory size among the two queues because it holds more information) has a limited queue size. On the other hand the instance queue is free to grow as needed. We need to have at least one of the two queues free to grow otherwise the process would get stuck as neither the info or the peer scraper can add anything to the queues. 

Both the info and peers scraper are asynchronous methods and the requests are executed with aiohttp. So even if they’ll be executed in the same process if one of them is waiting for a response from an API the other will be able to execute. 


## Code for scraping users

[instance_user_scanner.py, user_sorter.py]

Scraping users is a bit more difficult than fetching all the instances. The first major complication is that the followers and following of a certain user can only be requested to the instance where the user has originally registered.

If I try to fetch the followers of a user A from an instance I which isn’t its native one I will only get an incomplete answer: I will obtain the followers of user A who are native of instance I. To solve the problem the followers and following of a certain user must always be requested to its original instance (i.e. the one where it was registered). A further complication comes from the limited number of requests that each API offers: in order to take advantage as much as possible of the decentralized nature of the social network the API request should be divided among all the instances as evenly as possible. In other words we shouldn’t make one block of request to a single instance (with the resulting waiting time due to API limitation) while not exploiting all the other free instances. 

As we can see from the schema below the code is composed of two main parts: the sorter and an instance class. 

**Instance class**

One instance class will be created for each instance. Every five minutes the instance class makes 300 requests to the corresponding instance. These requests will be divided between id requests and followers/following requests: 



* Id requests starts from the id queue, here we’ll have the usernames of users belonging to this specific instance, thanks to the API endpoint ** /api/v2/search/?q={username} **we’ll fetch the numerical id of the user. With the numerical id we can compose the url to query the follower and following of each user, these URLs will be saved in the following and follower queues. 
* Following/followers requests start from the following and follower queue. From these queues we obtain the URL of the endpoint to which we can require the followers or followings of a certain user. If that user has more than 80 followers (or following) in the response we’ll also obtain a pagination link which will be added to the following and follower queues for the future requests. 



<p id="gdcalert2" ><span style="color: red; font-weight: bold">>>>>>  gd2md-html alert: inline image link here (to images/image2.png). Store image on your image server and adjust path/filename/extension if necessary. </span><br>(<a href="#">Back to top</a>)(<a href="#gdcalert3">Next alert</a>)<br><span style="color: red; font-weight: bold">>>>>> </span></p>


![alt_text](images/image2.png "image_tooltip")


Once we obtain the followers or following of a certain user these could either be users of the same instance of the user they follow or from another instance. If they’re from the same instance the id that we obtain (in the response of the followers request) can directly be used to fetch the followers and followings of the new user. 

If, on the other hand, the follower doesn’t belong to the same instance of the followed user, its identifier will be sent to the sort queue. 

If the followers queue, the following queue and id queue are all empty it means that there are currently no requests to be made. So, the class for that instance terminates its execution and gets removed from memory. If new users of that instance are found the class will be created again.  

**Sorter class**

When an instance finds a user (in the following and follower list) that doesn’t belong to the same instance it adds it to the sort queue. The user sorter sends each user from the sort queue to the corresponding instance. The url of the user is made of two parts: instance_name@username. So it allows the user sorter to add the user to the right id queue. In case a certain instance class isn’t present the sorter instantiates a new class. 


## Storage format

An example of a user json in mongoDB: 



<p id="gdcalert3" ><span style="color: red; font-weight: bold">>>>>>  gd2md-html alert: inline image link here (to images/image3.png). Store image on your image server and adjust path/filename/extension if necessary. </span><br>(<a href="#">Back to top</a>)(<a href="#gdcalert4">Next alert</a>)<br><span style="color: red; font-weight: bold">>>>>> </span></p>


![alt_text](images/image3.png "image_tooltip")


This is the json obtained as response when requiring information of a user from the API with a few additional fields:



* _id which allows to uniquely identify the user in the database
* followers/following: two lists where each element is the id of another user who followed or follows this user. 

The json saved for the instance has all the information obtained from the API, plus an additional attribute for the peers of the instance (a list). 



<p id="gdcalert4" ><span style="color: red; font-weight: bold">>>>>>  gd2md-html alert: inline image link here (to images/image4.png). Store image on your image server and adjust path/filename/extension if necessary. </span><br>(<a href="#">Back to top</a>)(<a href="#gdcalert5">Next alert</a>)<br><span style="color: red; font-weight: bold">>>>>> </span></p>


![alt_text](images/image4.png "image_tooltip")


Many instances don’t respond to the request of information (either because they don’t exist anymore or because they haven’t opened the API endpoint). We’ll also save the error message received by these instances: 



<p id="gdcalert5" ><span style="color: red; font-weight: bold">>>>>>  gd2md-html alert: inline image link here (to images/image5.png). Store image on your image server and adjust path/filename/extension if necessary. </span><br>(<a href="#">Back to top</a>)(<a href="#gdcalert6">Next alert</a>)<br><span style="color: red; font-weight: bold">>>>>> </span></p>


![alt_text](images/image5.png "image_tooltip")
