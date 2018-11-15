from neo4j.v1 import GraphDatabase, basic_auth
from secrets import *
import requests
import bs4
import nltk

driver = GraphDatabase.driver(BOLT_ADDRESS, auth=basic_auth(DB_NAME, DB_AUTH))


def do_work(job):
    if job[1] == "LinkedIn":
        linkedin_module(job[0])

    if job[1] == "TwitterNew":
        twitter_new_module(job[0])

    if job[1] == "Sentiment":
        sentiment_module(job[0])


def linkedin_module(job):
    session = driver.session()

    name = session.run("MATCH (n)\nWHERE id(n) = {id}\nRETURN n.name", id=job)
    names = [result["n.name"] for result in name]
    json = requests.get('http://127.0.0.1:8000/get/linkedin/employees/%s' % (names[0]))

    query = """WITH {json} as data
            UNWIND data.items as person
            MATCH (c)-[:HAS_TAG]->(t:Tag)
            WHERE id(c) = {id}
            SET c.LastSeenByLinkedIn = datetime()
            MERGE (la:LinkedInAccount {address: person.URL, workhistory: person.DatesEmployed})
            ON CREATE SET la.created = datetime(), la.createdBy = 'LinkedIn'
            ON MATCH SET la.LastSeenByLinkedIn = datetime()
            MERGE (la)-[:HAS_TAG]->(t)
            MERGE (p:Person {firstname: person.FirstName, lastname: person.LastName,company: person.Company})
            ON CREATE SET p.created = datetime(), p.createdBy = 'LinkedIn'
            ON MATCH SET p.LastSeenByLinkedIn = datetime()
            MERGE (p)-[:HAS_TAG]->(t)
            MERGE (p)-[:HAS_ACCOUNT]->(la)"""

    session.run(query, json=json.json(), id=job)

    query = """MATCH (p:Person)-[:HAS_TAG]->(t:Tag)<-[:HAS_TAG]-(c:Company)
            WHERE p.company = c.name
            MERGE (p)-[:WORKS_FOR]->(c)"""

    session.run(query, id=job)

    query = """MATCH (p:Person)-[:HAS_TAG]->(t:Tag)<-[:HAS_TAG]-(c:Company)
                    WHERE NOT p.company = c.name
                    MERGE (p)-[:WORKED_FOR]->(c)"""

    session.run(query, id=job)

    session.close()

def twitter_new_module(job):
    session = driver.session()

    handle = session.run("MATCH (n)\nWHERE id(n) = {id}\nRETURN n.handle", id=job)
    handles = [result["n.handle"] for result in handle]
    json = requests.get('http://127.0.0.1:8000/get/twitter/tweets/%s' % (handles[0]))

    query = """WITH {json} as data
            UNWIND data.items as tweet
            MATCH (c)-[:HAS_TAG]->(t:Tag)
            WHERE id(c) = {id}
            SET c.LastSeenByTwitter = datetime()
            MERGE (tw:Tweet {id: tweet.id, text: tweet.text})
            ON CREATE SET tw.created = datetime(), tw.createdBy = 'TwitterNew', tw.LastSeenByTwitter = datetime()
            ON MATCH SET tw.LastSeenByTwitter = datetime()
            MERGE (tw)-[:HAS_TAG]->(t)
            MERGE (c)-[:HAS_TWEET]->(tw)"""

    session.run(query, json=json.json(), id=job)

    session.close()


def sentiment_module(job):
    session = driver.session()

    text = session.run("MATCH (n)\nWHERE id(n) = {id}\nRETURN n.text", id=job)
    texts = [result["n.text"] for result in text]

    soup = bs4.BeautifulSoup(texts[0]).get_text()
    input = nltk.Text(soup)

    print(soup)

    json = requests.get('http://127.0.0.1:8000/get/sentiment/%s' % (input.concordance))

    if json.status_code == 200:
        query = """WITH {json} as data
                UNWIND data.items as sentiment
                MATCH (c)-[:HAS_TAG]->(t:Tag)
                WHERE id(c) = {id}
                SET c.LastSeenBySentiment = datetime(),
                c.polarity = sentiment.polarity,
                c.subjectivity = sentiment.subjectivity"""

        session.run(query, json=json.json(), id=job)

    session.close()