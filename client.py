import streamlit as st
import requests
import json
import pandas as pd
import io

st.set_page_config(page_title="MCP Client", layout="wide")
st.title("MCP Client")

# Server URL
server_url = st.sidebar.text_input("Server URL", "http://localhost:808s0/api/mcp")
debug_mode = st.sidebar.checkbox("Debug Mode", value=True)

# Test connection
if st.sidebar.button("Test Connection"):
    try:
        response = requests.get(f"http://{server_url.split('/api/')[0].split('//')[1]}")
        st.sidebar.success(f"Server is running: {response.json()}")
    except Exception as e:
        st.sidebar.error(f"Connection error: {str(e)}")

# Data input
st.header("Enter Data")
data_type = st.radio("Data Type", ["List of Numbers", "Dictionary of Lists", "Upload JSON File"])

data = None

if data_type == "List of Numbers":
    numbers_input = st.text_area("Enter numbers (one per line)", "1\n2\n3\n4\n5")
    
    try:
        numbers = [float(x.strip()) for x in numbers_input.split("\n") if x.strip()]
        if numbers:
            st.success(f"Valid input: {len(numbers)} numbers")
            data = numbers
        else:
            st.error("Please enter at least one number")
            data = None
    except ValueError:
        st.error("Invalid input. Please enter numbers only.")
        data = None

elif data_type == "Dictionary of Lists":
    if "dict_pairs" not in st.session_state:
        st.session_state.dict_pairs = [{"key": "group1", "values": "1,2,3,4,5"}]
    
    # Display pairs
    data_dict = {}
    for i, pair in enumerate(st.session_state.dict_pairs):
        col1, col2 = st.columns([1, 3])
        
        with col1:
            key = st.text_input(f"Key #{i+1}", pair["key"], key=f"key_{i}")
        
        with col2:
            values = st.text_input(f"Values (comma separated)", pair["values"], key=f"values_{i}")
        
        pair["key"] = key
        pair["values"] = values
        
        try:
            numbers = [float(x.strip()) for x in values.split(",") if x.strip()]
            if numbers:
                data_dict[key] = numbers
        except ValueError:
            st.error(f"Invalid values for {key}")
    
    # Add/remove buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Add Group"):
            st.session_state.dict_pairs.append({"key": f"group{len(st.session_state.dict_pairs)+1}", "values": ""})
            st.rerun()
    
    with col2:
        if st.button("Remove Last Group") and len(st.session_state.dict_pairs) > 1:
            st.session_state.dict_pairs.pop()
            st.rerun()
    
    if data_dict:
        st.success(f"Valid input: {len(data_dict)} groups")
        data = data_dict
    else:
        st.error("Please enter at least one valid group")
        data = None

else:  # Upload JSON File
    st.subheader("Upload JSON File")
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a JSON file", type=["json"])
    
    if uploaded_file is not None:
        try:
            # Read the file
            content = uploaded_file.getvalue().decode("utf-8")
            
            # Parse JSON
            json_data = json.loads(content)
            
            # Validate the structure
            if isinstance(json_data, list):
                # Check if it's a list of numbers
                try:
                    numbers = [float(x) for x in json_data]
                    st.success(f"Valid JSON: List of {len(numbers)} numbers")
                    data = numbers
                except (ValueError, TypeError):
                    st.error("Invalid JSON: List must contain only numbers")
                    data = None
                    
            elif isinstance(json_data, dict):
                # Check if it's a dictionary of lists of numbers
                valid_data = {}
                invalid_keys = []
                
                for key, value in json_data.items():
                    if isinstance(value, list):
                        try:
                            numbers = [float(x) for x in value]
                            valid_data[key] = numbers
                        except (ValueError, TypeError):
                            invalid_keys.append(key)
                    else:
                        invalid_keys.append(key)
                
                if invalid_keys:
                    st.error(f"Invalid values for keys: {', '.join(invalid_keys)}")
                
                if valid_data:
                    st.success(f"Valid JSON: Dictionary with {len(valid_data)} groups")
                    data = valid_data
                else:
                    st.error("No valid data found in the JSON file")
                    data = None
            else:
                st.error("Invalid JSON: Must be a list of numbers or a dictionary of lists")
                data = None
                
            # Display a preview
            if data is not None:
                st.subheader("Data Preview")
                
                if isinstance(data, list):
                    preview = data[:10] if len(data) > 10 else data
                    st.write(f"List: {preview}")
                    if len(data) > 10:
                        st.caption(f"... and {len(data) - 10} more items")
                else:
                    st.write("Dictionary:")
                    for key, value in list(data.items())[:5]:
                        preview = value[:5] if len(value) > 5 else value
                        st.write(f"- {key}: {preview}")
                        if len(value) > 5:
                            st.caption(f"  ... and {len(value) - 5} more items")
                    if len(data) > 5:
                        st.caption(f"... and {len(data) - 5} more groups")
        
        except json.JSONDecodeError:
            st.error("Invalid JSON format. Please upload a valid JSON file.")
            data = None
        except Exception as e:
            st.error(f"Error processing the file: {str(e)}")
            data = None

# Operation selection
operation = st.selectbox("Select Operation", ["mean", "sum", "median", "min", "max"])

# Analysis button
if st.button("Analyze Data", disabled=data is None) and data is not None:
    payload = {
        "data": data,
        "operation": operation
    }
    
    if debug_mode:
        st.subheader("Request Payload")
        st.code(json.dumps(payload, indent=2))
    
    try:
        with st.spinner("Processing..."):
            response = requests.post(server_url, json=payload)
        
        if debug_mode:
            st.subheader("Response")
            st.write(f"Status Code: {response.status_code}")
            st.code(response.text)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("status") == "success":
                st.header("Result")
                
                if isinstance(result["result"], dict):
                    df = pd.DataFrame({
                        "Group": list(result["result"].keys()),
                        f"{operation.capitalize()} Value": list(result["result"].values())
                    })
                    st.dataframe(df)
                    st.bar_chart(df.set_index("Group"))
                else:
                    st.metric(operation.capitalize(), f"{result['result']:.4f}")
            else:
                st.error(f"Error: {result.get('error', 'Unknown error')}")
        else:
            st.error(f"Server error: {response.status_code}")
            st.error(response.text)
    
    except Exception as e:
        st.error(f"Request error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
