# Microsoft Azure VM Deployment Guide — GateFlow

This guide provides step-by-step instructions to deploy the GateFlow API application onto a dedicated Linux Virtual Machine (VM) on Microsoft Azure. This is an excellent way to utilize your Azure credits with complete control over your infrastructure.

---

## Prerequisites

1. **Azure CLI (`az`)** installed and initialized:
   - Run `az --version` to check.
   - If not installed, download it from the [official Microsoft documentation](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli).
2. **Authenticate with Azure**:
   - Run `az login` to authenticate with your Microsoft account.
3. **Active Subscription**:
   - Ensure you have an active Azure subscription (e.g., your $100 credit account).

---

## Deployment Steps

### 1. Create a Resource Group
A resource group is a logical container into which Azure resources are deployed and managed.
```bash
az group create --name GateFlowResourceGroup --location eastus
```
*(You can change `eastus` to a region closer to you, like `westus`, `westeurope`, or `centralindia`).*

### 2. Provision the Virtual Machine
We will create an Ubuntu Linux VM (`Standard_B2s` size is cost-effective and provides 2 vCPUs and 4GB RAM, perfect for this application).

Run this command to create the VM and generate SSH keys:
```bash
az vm create \
  --resource-group GateFlowResourceGroup \
  --name GateFlowVM \
  --image Ubuntu2204 \
  --admin-username azureuser \
  --size Standard_B2s \
  --generate-ssh-keys
```
*Note: This command will output JSON containing your VM's `publicIpAddress`. Save this IP address, as you will need it later.*

### 3. Open Port 8000 for Web Traffic
GateFlow runs on port 8000 by default. We need to allow inbound traffic on this port:
```bash
az vm open-port --resource-group GateFlowResourceGroup --name GateFlowVM --port 8000
```

### 4. Connect to the Virtual Machine
SSH into your new VM using the `publicIpAddress` from Step 2:
```bash
ssh azureuser@<YOUR_PUBLIC_IP_ADDRESS>
```

---

## Application Setup (Run inside the VM)

Now that you are connected to the VM, run the following commands to install Docker and start GateFlow.

### 5. Install Docker
Install Docker on the Ubuntu VM:
```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl enable --now docker
# Add the current user to the docker group to run docker commands without sudo
sudo usermod -aG docker $USER
```
*Tip: You may need to disconnect (`exit`) and SSH back into the VM for the group changes to take effect.*

### 6. Clone the Repository
Clone your GateFlow repository onto the VM:
```bash
git clone https://github.com/bhadanevinay/GateFlow---Smart-Stadiums-Tournament-Operations.git
cd GateFlow---Smart-Stadiums-Tournament-Operations
```

### 7. Create Environment Variables (Optional)
If you want to use the live Gemini Phrasing layer, create a `.env` file from the example and add your API key:
```bash
cp .env.example .env
nano .env # Add your GEMINI_API_KEY here and save
```
*(If you skip this step, GateFlow will automatically use the offline template phrasing layer).*

### 8. Build and Run the Application
Build the Docker container and run it in detached mode (`-d`) so it keeps running after you disconnect:
```bash
docker build -t gateflow-app .
docker run -d -p 8000:8000 --name gateflow-container --env-file .env gateflow-app
```
*(If you didn't create a `.env` file, simply omit the `--env-file .env` flag).*

---

## Verification

To verify that your deployment is live and working:

1. **Test the health endpoint**:
   Open your local browser and navigate to:
   ```
   http://<YOUR_PUBLIC_IP_ADDRESS>:8000/health
   ```
   *Expected response:* `{"status":"ok"}`

2. **Access the web interface**:
   Open `http://<YOUR_PUBLIC_IP_ADDRESS>:8000/` in your browser to view the interactive dashboard.

3. **Explore interactive API docs**:
   Navigate to `http://<YOUR_PUBLIC_IP_ADDRESS>:8000/docs` to test endpoints via the OpenAPI Swagger UI.

---

## Clean Up (Optional)
When you are done and want to stop incurring charges against your credits, you can delete the entire resource group, which destroys the VM and all associated resources:
```bash
az group delete --name GateFlowResourceGroup --yes --no-wait
```
