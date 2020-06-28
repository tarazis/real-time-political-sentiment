from flask import Flask,jsonify,request
from flask import render_template
# from mpl_toolkits.basemap import Basemap
import geopandas
import ast
app = Flask(__name__)

liberalData = []
conservativeData = []
ndpData = []

@app.route("/")
def get_chart_page():
    print("hi!!")
    global liberalData, conservativeData, ndpData
    liberalData = []
    conservativeData = []
    ndpData = []
    return render_template('chart.html', liberalData=liberalData, conservativeData=conservativeData, ndpData=ndpData)


@app.route('/refreshData')
def refresh_graph_data():
    global liberalData, conservativeData, ndpData
    print("hi!!refresh data")

    print("liberals now: " + str(liberalData))
    print("conservatives now: " + str(conservativeData))
    print("ndp now: " + str(ndpData))

    return jsonify(liberalData=liberalData, conservativeData=conservativeData, ndpData=ndpData)


@app.route('/updateData', methods=['POST'])
def update_data():
    print("hi!! data")
    global liberalData, conservativeData, ndpData
    if not request.form:
        return "error",400

    liberalData = ast.literal_eval(request.form['liberal'])
    conservativeData = ast.literal_eval(request.form['conservative'])
    ndpData = ast.literal_eval(request.form['ndp'])

    print("liberals received: " + str(liberalData))
    print("conservatives received: " + str(conservativeData))
    print("ndp received: " + str(ndpData))
    refresh_graph_data()
    return "success",201


if __name__ == "__main__":
    app.run(host='10.24.235.161', port=5001)