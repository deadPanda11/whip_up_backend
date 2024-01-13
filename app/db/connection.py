from pymongo import MongoClient

mongodb_uri = 'mongodb+srv://samia:samia@cluster0.msh0bbr.mongodb.net/?retryWrites=true&w=majority'
client = MongoClient(mongodb_uri)
db = client.newUsers
# assuming 'customerdata' is the name of your database

__all__ = ['db']


def check_db_connection():
    try:
        client.server_info()  # This will raise an exception if the connection is not successful
        return True
    except Exception as e:
        return str(e)
