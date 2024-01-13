from pymongo import MongoClient

mongodb_uri = 'mongodb+srv://samia:samia@cluster0.msh0bbr.mongodb.net/?retryWrites=true&w=majority'
client = MongoClient(mongodb_uri)
db = client.newUsers  # assuming 'customerdata' is the name of your database
