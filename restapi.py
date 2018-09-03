from flask import Flask, jsonify
from flask_restful import Resource, Api
from neo4j.v1 import GraphDatabase, basic_auth


driver = GraphDatabase.driver("bolt://hobby-egcmkjgcconogbkekpcmcobl.dbs.graphenedb.com:24786", auth=basic_auth("csa-laptop", "b.xAEJfrSq4KEn.tTSqgx0mSYCQq2Vx"))


# Connect to neo4j
app = Flask(__name__) #initializing web framework
api = Api(app)         #creating api


class Config(object):                       # Config for FLASK
    JSONIFY_PRETTYPRINT_REGULAR = True      # JSONIFY will indent and space if true


app.config.from_object(Config)

class GetLinkedInEmployees(Resource):
    def get(self, project_name,company_name):
        session = driver.session()

        cypher = "MATCH ( %s:tag {name: '%s' } )\n" % (project_name, project_name)
        cypher += "MERGE ( %s:Company { name: '%s'})\n" % (company_name, company_name)
        cypher += "MERGE (%s) - [r: HAS_TAG] -> (%s)\n" % (project_name, company_name)
        cypher += "ON CREATE SET %s.created = timestamp() + ' by LinkedIn'," % (project_name)
        cypher += " %s.created = timestamp() + ' by LinkedIn'\n" % (company_name)
        cypher += "ON MATCH SET %s.LinkedInModded = timestamp()," % (project_name)
        cypher += " %s.LinkedInModded = timestamp()\n" % (company_name)
        cypher += "RETURN %s.name, type(r), %s.name" % (project_name, company_name)

        query = session.run(cypher)
        session.close()

        results = []
        for result in query:
            results.append({"tag.name:": result["%s.name" % (project_name)],
                            "has.relationship:": result["type(r)"],
                            "tag.name:": result["%s.name" % (company_name)]})
        return jsonify(results)      # replace w/result


api.add_resource(GetLinkedInEmployees, '/get/linkedin/employees/<project_name>/<company_name>')


if __name__ == '__main__':  # run api on 127.0.0.1:5002
    app.run(port='5002')