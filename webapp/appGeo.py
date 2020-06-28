import json

from flask import Flask,jsonify,request
from flask import render_template
# from mpl_toolkits.basemap import Basemap
import geopandas
import ast
app = Flask(__name__)

# liberalData = []
# conservativeData = []
# ndpData = []

provinceDict = {}

@app.route("/")
def get_chart_page():
    print("hi!!")
    # global liberalData, conservativeData, ndpData
    global provinceDict
    provinceDict = {}

    # liberalData = []
    # conservativeData = []
    # ndpData = []
    return render_template('chartGeo.html', provinceDict=provinceDict)


@app.route('/refreshData')
def refresh_graph_data():
    # global liberalData, conservativeData, ndpData
    global provinceDict

    print("hi!!refresh data")

    # print("liberals now: " + str(liberalData))
    # print("conservatives now: " + str(conservativeData))
    # print("ndp now: " + str(ndpData))

    print(provinceDict)

    return jsonify(provinceDict=provinceDict)


@app.route('/updateData', methods=['POST'])
def update_data():
    print("hi!! data")
    global provinceDict

    try:
        provinceDict = request.get_json()
        print(provinceDict)

    except:
        print("error again")

    refresh_graph_data()
    return "success",201


if __name__ == "__main__":
    app.run(host='10.24.235.161', port=5001)