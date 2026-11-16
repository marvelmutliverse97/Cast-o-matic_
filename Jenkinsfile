pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Install Dependencies') {
            steps {
                bat 'python -m pip install -r requirements.txt'
            }
        }

        stage('Run Tests') {
            steps {
                bat 'python -m unittest discover -s tests -t . -v'
            }
        }

        stage('Build Docker Image') {
            steps {
                bat 'docker build -t cast-o-matic:latest .'
            }
        }
    }

    post {
        success { echo 'Cast-O-Matic pipeline completed successfully.' }
        failure { echo 'Cast-O-Matic pipeline failed. Check the console output.' }
    }
}
