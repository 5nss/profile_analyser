# Profile Analyzer

## Deployment Instructions for Streamlit Cloud

1. **Create a Streamlit Cloud Account**: If you don’t have an account, sign up at [Streamlit Cloud](https://streamlit.io/cloud).

2. **Link Your GitHub Repository**: Once logged in, connect your GitHub account and select the `5nss/profile_analyser` repository.

3. **Deploy Your App**:
   - Click on the "New App" button.
   - Choose the branch (default is `main`) and specify the path to your Streamlit file (e.g., `app.py`).
   - Click on "Deploy."

4. **Set Environment Variables (if needed)**: If your app requires any environment variables, set them in the Streamlit Cloud app settings.

5. **After Deployment**: Once the app is deployed, Streamlit Cloud provides a URL to access your app. 

6. **Updates**: To update your app, push changes to the GitHub repository, and Streamlit Cloud will automatically redeploy the app.

## Additional Notes
- Make sure your `requirements.txt` file is present in the repository to install the necessary packages for the deployment.