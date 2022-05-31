
import csv
import json
import uuid
import struct
import matplotlib
import matplotlib.cm
import pandas as pd
import sys, getopt
# Function to convert a CSV to JSON
# Takes the file paths as arguments


#takes one input file to convert to json. 
#makes one layer file for each class.
def make_json(csvFilePath, outputFilePath):

    cmaps = ["jet","hsv","BrBG"]

    fields_arr = []
    df = pd.read_csv(csvFilePath, header=0)
    cmax = df["index"].max()
    cmin = df["index"].min()
    norm = matplotlib.colors.Normalize(vmin=cmin, vmax=cmax)  #NH: Not sure if this is necessary if the values are already between 0 and 1, check back with group. Example values are between 0.3 and 0.5
    cmap = matplotlib.cm.get_cmap("tab20") #colourmap to classify  

    #fixedColumns should be in all input files. any extra columns will be treated as parameters which can be used with a colormap.
    fixedColumns = ["id","x","y","z","eux","euy","euz","index","mrc_file","name"]
    for col in df.columns:
       
        if col not in fixedColumns:
             print("Found data column named: " + col)
             fields_arr.append({"name":col, "min": df[col].min(), "max":df[col].max()})
    #go through fields and make colourmaps for each
    index = 0
    res = {"columns":[]}
    #read the extra column data defined in the header field. add this to "columns" which will later be used to be able to colour by extra columns.
    for item in fields_arr:
        item['val_norm'] = matplotlib.colors.Normalize(vmin=item['min'], vmax=item['max'])
        item['cmap'] = matplotlib.cm.get_cmap(cmaps[index]) #assign a new colourmap for each field
        index+=1
        res["columns"].append(item["name"])

    for index, row in df.iterrows():
        val = norm(float(row["index"]))
        
        #print(row["type"])
        if (row["name"] not in res.keys() ):
            res[row["name"]]=[]
        #print(res[str(val)])
        cval = cmap(float(val))

        #calculate the columns
        #column_obj = []
        props =[matplotlib.colors.to_hex(cval)]
        desc_str = ""
        fields = {}
        for item in fields_arr:
           
            item_val = item['val_norm'](row[item['name']])
            cmap_val = item['cmap'](item_val)
            #column_obj.append({item["name"]:cmap_val})
            desc_str+=item["name"] +": " + str(row[item['name']])
            props.append(matplotlib.colors.to_hex(cmap_val))
            fields[item["name"]]=item_val
        
        if(desc_str == ""):
            desc_str = "no further data"
        
        #convert id with possible string characters to numbers only, 
        # necessary for later mesh generation which requires numerical ids.
      
        arr = [str(ord(c)) for c in row["id"]]
        num_id = ''.join(arr)
        #print(num_id)
        res[row["name"]].append({"type": "point", 
        "description": desc_str, 
        "id":num_id+str(index), 
        "point": [float(row["x"]), float(row["y"])  ,float(row["z"])], 
        "props": props,
        "fields": fields })
    for type_ in res.keys():
        with open(outputFilePath + "/"+type_.strip()  +".json", 'w', encoding='utf-8') as jsonf:
            jsonf.write(json.dumps(res[type_], indent=4))
    #print(res["columns"])
    print("Annotation processing done")
    print("Layers have been created dataset/coordinates folder.")

if __name__ == "__main__":
    inputfile = ''
    outputfile = ''
    headerfile = ''
    #print(sys.argv)
    print(" Starting Annotation Layer conversion ... ")
    try:
        opts, args = getopt.getopt(sys.argv[1:],"hi:o:",["ifile=","ofile="])
    except getopt.GetoptError:
        print("error. Usage: ")
        print('Annotation_Layer.py -i <inputfile> -o <outputfolder>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('Annotation_Layer.py -i <inputfile> -o <outputfolder>')
            sys.exit()
        elif opt in ("-i", "--ifile"):
            inputfile = arg
        elif opt in ("-o", "--ofile"):
            outputfile = arg


    make_json(inputfile,outputfile)
#csvFilePath = r'synthetic/particles/particles.csv'
#outputFilePath = r'synthetic/particles//particles_export.json'
 
# Call the make_json function
#make_json(csvFilePath, outputFilePath)