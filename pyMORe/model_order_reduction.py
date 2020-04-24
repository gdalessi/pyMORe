'''
MODULE: model_order_reduction.py

@Authors:
    G. D'Alessio [1,2]
    [1]: Université Libre de Bruxelles, Aero-Thermo-Mechanics Laboratory, Bruxelles, Belgium
    [2]: CRECK Modeling Lab, Department of Chemistry, Materials and Chemical Engineering, Politecnico di Milano

@Contacts:
    giuseppe.dalessio@ulb.ac.be


@Additional notes:
    This code is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
    Please report any bug to: giuseppe.dalessio@ulb.ac.be

'''

import numpy as np
from numpy import linalg as LA
import matplotlib
import matplotlib.pyplot as plt

from .utilities import *
from . import clustering

class PCA:
    def __init__(self, X):
        #Useful variables from training dataset
        self.X = X
        self.n_obs = X.shape[0]
        self.n_var = X.shape[1]

        #Decide if the input matrix must be centered:
        self._center = True
        #Set the centering method:
        self._centering = 'mean'                                                                    #'mean' or 'min' are available
        #Decide if the input matrix must be scaled:
        self._scale = True
        #Set the scaling method:
        self._scaling = 'auto'                                                                      #'auto';'vast';'range';'pareto' are available
        #Enable the plotting property to show the explained variance
        self._plot_explained_variance = True
        #Automatically assess the number of PCs to retain with one of the available methods
        self._assessPCs = 'var'                                                                     #False (bool) = skip; 'var' = explained variance criterion; 'nrmse' = average reconstruction error
        self._threshold_var = 0.95                                                                  # threshold in case of explained variance assessment criterion
        self._threshold_nrmse = 0.1                                                                 # treshold in case of reconstruction error criterion
        #Set the PC number to plot or the variable's number to plot
        self._num_to_plot = 1
        #Initialize the number of PCs
        self._nPCs = X.shape[1] -1

    @property
    def eigens(self):
        return self._nPCs

    @eigens.setter
    @accepts(object, int)
    def eigens(self, new_value):
        self._nPCs = new_value

        if self._nPCs <= 0:
            raise Exception("The number of Principal Components must be a positive integer. Exiting..")
            exit()
        elif self._nPCs >= self.n_var:
            raise Exception("The number of PCs exceeds (or is equal to) the number of variables in the data-set. Exiting..")
            exit()

    @property
    def to_center(self):
        return self._center

    @to_center.setter
    @accepts(object, bool)
    def to_center(self, new_bool):
        self._center = new_bool


    @property
    def centering(self):
        return self._centering

    @centering.setter
    @allowed_centering
    def centering(self, new_string):
        self._centering = new_string


    @property
    def to_scale(self):
        return self._scale

    @to_scale.setter
    @accepts(object, bool)
    def to_scale(self, new_bool):
        self._scale = new_bool


    @property
    def scaling(self):
        return self._scaling

    @scaling.setter
    @allowed_scaling
    def scaling(self, new_string):
        self._scaling = new_string

    @property
    def plot_explained_variance(self):
        return self._plot_explained_variance

    @plot_explained_variance.setter
    @accepts(object, bool)
    def plot_explained_variance(self, new_bool):
        self._plot_explained_variance = new_bool

    @property
    def set_explained_variance_perc(self):
        return self._explained_variance

    @set_explained_variance_perc.setter
    @accepts(object, float)
    def set_explained_variance_perc(self, new_value):
        self._explained_variance = new_value

    @property
    def set_PCs_method(self):
        return self._assessPCs

    @set_PCs_method.setter
    def set_PCs_method(self, new_method):
        self._assessPCs = new_method

    @property
    def set_num_to_plot(self):
        return self._assessPCs

    @set_num_to_plot.setter
    @accepts(object, int)
    def set_num_to_plot(self, new_number):
        self._assessPCs = new_number


    @staticmethod
    def preprocess_training(X, centering_decision, scaling_decision, centering_method, scaling_method):

        if centering_decision and scaling_decision:
            mu, X_ = center(X, centering_method, True)
            sigma, X_tilde = scale(X_, scaling_method, True)
        elif centering_decision and not scaling_decision:
            mu, X_tilde = center(X, centering_method, True)
        elif scaling_decision and not centering_decision:
            sigma, X_tilde = scale(X, scaling_method, True)
        else:
            X_tilde = X

        return X_tilde


    def fit(self):
        '''
        Perform Principal Component Analysis on the dataset X,
        and retain 'n' Principal Components. The covariance matrix
        is firstly calculated, then it is decomposed in eigenvalues
        and eigenvectors. Lastly, the eigenvalues are ordered depending
        on their magnitude and the associated eigenvectors (the PCs)
        are retained.

        - Output:
        evecs: eigenvectors from the covariance matrix decomposition (PCs)
        evals: eigenvalues from the covariance matrix decomposition (lambda)

        !!! WARNING !!! the PCs are already ordered (decreasing, for importance)
        because the eigenvalues are also ordered in terms of magnitude.
        '''
        #Center and scale the original training dataset
        self.X_tilde = self.preprocess_training(self.X, self._center, self._scale, self._centering, self._scaling)

        #Compute the covariance matrix
        C = np.cov(self.X_tilde, rowvar=False) #rowvar=False because the X matrix is (observations x variables)

        self.ALLevals, self.ALLevecs = LA.eig(C)
        mask = np.argsort(self.ALLevals)[::-1]
        self.evecs = self.ALLevecs[:,mask]
        self.evals = self.ALLevals[mask]

        self.evecs = self.evecs[:,:self._nPCs]
        self.evals = self.evals[:self._nPCs]

        return self.evecs, self.evals


    def recover(self):
        '''
        Reconstruct the original matrix from the reduced PCA-manifold.

        - Output:
        X_rec = uncentered and unscaled reconstructed matrix with PCA modes -- dim: (observations x variables)
        '''

        #Compute the centering and the scaling factors. Later they will be useful.
        self.mu = center(self.X, self.centering)
        self.sigma = scale(self.X, self.scaling)
        #Reconstruct the original matrix
        self.X_r = self.X_tilde @ self.evecs @ self.evecs.T
        # Uncenter and unscale to get the reconstructed original matrix
        X_unsc = unscale(self.X_r, self.sigma)
        self.X_rec = uncenter(X_unsc, self.mu)

        return self.X_rec


    def get_explained(self):
        '''
        Assess the variance explained by the first 'n_eigs' retained
        Principal Components. This is important to know if the percentage
        of explained variance is enough, or additional PCs must be retained.
        Usually, it is considered accepted a percentage of explained variable
        above 95%.

        - Output:
        explained: percentage of explained variance -- dim: (scalar)
        '''
        explained_variance = np.cumsum(self.evals)/sum(self.ALLevals)
        explained = explained_variance[-1]
        #If the plot boolean is True, produce an image to show the explained variance curve.
        if self._plot_explained_variance:
            matplotlib.rcParams.update({'font.size' : 18, 'text.usetex' : True})
            fig = plt.figure()
            axes = fig.add_axes([0.15,0.15,0.7,0.7], frameon=True)
            axes.plot(np.linspace(1, len(explained_variance), len(explained_variance)), explained_variance, color='b', marker='s', linestyle='-', linewidth=2, markersize=4, markerfacecolor='b', label='Cumulative explained')
            axes.plot([self.eigens, self.eigens], [explained_variance[0], explained_variance[-1]], color='r', marker='s', linestyle='-', linewidth=2, markersize=4, markerfacecolor='r', label='Explained by {} PCs'.format(self.eigens))
            axes.set_xlabel('Number of PCs [-]')
            axes.set_ylabel('Explained variance [-]')
            axes.set_title('Variance explained by {} PCs: {}'.format(self.eigens, round(explained,3)))
            axes.legend()
        plt.show()

        return explained


    def get_scores(self):
        '''
        Project the original data matrix (cent and scaled) X_tilde
        on the low dimensional manifold spanned by the first 'n'
        Principal Components and obtain the scores matrix (Z).
        '''
        self.scores = self.X_tilde @ self.evecs

        return self.scores


    def set_PCs(self):
        optimalPCs = None
        if self._assessPCs != False:
            self.plot_explained_variance = False
            for ii in range(1, self.n_var):
                #print("Assessing the optimal number of PCs by means of: " + self._assessPCs + " criterion. Now using: {} Principal Component(s).".format(ii))

                self.eigens = ii
                self.fit()
                #Assess the optimal number of PCs by means of the explained variance threshold (>= 99% explained is the default setting)
                if self._assessPCs == 'var':
                    explained = self.get_explained()

                    if explained >= self._threshold_var:
                        #print("With {} PCs, the following percentage of variance is explained: {}".format(self.eigens, explained))
                        #print("The variance is larger than the given fixed threshold: {}. Thus, {} PCs will be retained.".format(self._threshold_var, self.eigens))
                        self.plot_explained_variance = True
                        optimalPCs = ii
                        break
                #Otherwise with the nrmse of the reconstructed matrix, which has to be below a specific threshold (<= 10% error is the default setting)
                elif self._assessPCs == 'nrmse':
                    reconstructed_ = self.recover()
                    variables_reconstruction = NRMSE(self.X, reconstructed_)

                    if np.mean(variables_reconstruction) <= self._threshold_nrmse:
                        print("With {} PCs, the following average error (NRMSE) for the variables reconstruction (from the PCA manifold) is obtained: {}".format(self.eigens, np.mean(variables_reconstruction)))
                        print("The error is lower than the given fixed threshold: {}. Thus, {} PCs will be retained.".format(self._threshold_nrmse, self.eigens))
                        optimalPCs = ii
                        break
        return optimalPCs


    def plot_PCs(self):
        '''
        Plot the variables' weights on a selected Principal Component (PC).
        The PCs are linear combination of the original variables: examining the
        weights, especially for the PCs associated with the largest eigenvalues,
        can be important for data-analysis purposes.

        '''

        matplotlib.rcParams.update({'font.size' : 18, 'text.usetex' : True})
        fig = plt.figure()
        axes = fig.add_axes([0.15,0.15,0.7,0.7], frameon=True)

        x = np.linspace(1, self.n_var, self.n_var)
        axes.bar(x, self.evecs[:,self._num_to_plot])
        axes.set_xlabel('Variables [-]')
        axes.set_ylabel('Weights on the PC number: {} [-]'.format(self._num_to_plot))
        plt.show()


    def plot_parity(self):
        '''
        Print the parity plot of the reconstructed profile from the PCA
        manifold. The more the scatter plot (black dots) is in line with the
        red line, the better it is the reconstruction.

        '''

        self.fit()
        reconstructed_ = self.recover()

        matplotlib.rcParams.update({'font.size' : 18, 'text.usetex' : True})
        fig = plt.figure()
        axes = fig.add_axes([0.25,0.15,0.7,0.7], frameon=True)
        axes.plot(self.X[:,self._num_to_plot], self.X[:,self._num_to_plot], color='r', linestyle='-', linewidth=2, markerfacecolor='b')
        axes.scatter(self.X[:,self._num_to_plot], reconstructed_[:,self._num_to_plot], 1, color= 'k')
        axes.set_xlabel('Original variable')
        axes.set_ylabel('Reconstructed from PCA manifold')
        plt.xlim(min(self.X[:,self._num_to_plot]), max(self.X[:,self._num_to_plot]))
        plt.ylim(min(self.X[:,self._num_to_plot]), max(self.X[:,self._num_to_plot]))
        #axes.set_title('Parity plot')
        plt.show()


    def outlier_removal_leverage(self):
        '''
        This function removes the multivariate outliers (leverage) eventually contained
        in the training dataset, via PCA. In fact, examining the data projection
        on the PCA manifold (i.e., the scores), and measuring the score distance
        from the manifold center, it is possible to identify the so-called
        leverage points. They are characterized by very high distance from the
        center of mass, once detected they can easily be removed.
        Additional info on outlier identification and removal can be found here:

        Jolliffe pag 237 --- formula (10.1.2):

        dist^{2}_{2,i} = sum_{k=p-q+1}^{p}(z^{2}_{ik}/l_{k})
        where:
        p = number of variables
        q = number of required PCs
        i = index to count the observations
        k = index to count the PCs

        '''
        #Leverage points removal:
        #Compute the PCA scores. Override the eventual number of PCs: ALL the
        #PCs are needed, as the outliers are given by the last PCs examination
        input_eigens = self.eigens
        self.eigens = self.X.shape[1]-1
        PCs, eigval = self.fit()
        scores = self.get_scores()
        TOL = 1E-16
        #put again the user-defined number of PCs
        self.eigens = input_eigens

        scores_dist = np.empty((self.X.shape[0],), dtype=float)
        #For each observation, compute the distance from the center of the manifold
        for ii in range(0,self.X.shape[0]):
            t_sq = 0
            lam_j = 0
            for jj in range(input_eigens, scores.shape[1]):
                t_sq += scores[ii,jj]**2
                lam_j += eigval[jj]
            scores_dist[ii] = t_sq/(lam_j + TOL)

        #Now compute the distance distribution, and delete the observations in the
        #upper 3% (done in the while loop) to get the outlier-free matrix.

        #Divide the distance vector in 100 bins
        n_bins = 100
        min_interval = np.min(scores_dist)
        max_interval = np.max(scores_dist)

        delta_step = (max_interval - min_interval) / n_bins

        counter = 0
        bin = np.empty((len(scores_dist),))
        var_left = min_interval

        #Find the observations in each bin (find the idx, where the classes are
        #the different bins number)
        while counter <= n_bins:
            var_right = var_left + delta_step
            mask = np.logical_and(scores_dist >= var_left, scores_dist < var_right)
            bin[np.where(mask)] = counter
            counter += 1
            var_left += delta_step

        unique,counts=np.unique(bin,return_counts=True)
        cumulativeDensity = 0
        new_counter = 0

        while cumulativeDensity < 0.98:
            cumulative_ = counts[new_counter]/self.X.shape[0]
            cumulativeDensity += cumulative_
            new_counter += 1

        new_mask = np.where(bin > new_counter)
        self.X = np.delete(self.X, new_mask, axis=0)

        return self.X , bin, new_mask



    def outlier_removal_orthogonal(self):
        '''
        This function removes the multivariate outliers (orthogonal out) eventually contained
        in the training dataset, via PCA. In fact, examining the reconstruction error
        it is possible to identify the so-called orthogonal outliers. They are characterized
        by very high distance from the manifold (large rec error), once detected they can easily
        be removed.
        Additional info on outlier identification and removal can be found here:

        Hubert, Mia, Peter Rousseeuw, and Tim Verdonck. Computational Statistics & Data Analysis 53.6 (2009): 2264-2274.

        '''
        #Orthogonal outliers removal:
        PCs, eigval = self.fit()

        mu_X = center(self.X, self.centering)
        sigma_X = scale(self.X, self.scaling)

        X_cs = center_scale(self.X, mu_X, sigma_X)


        epsilon_rec = X_cs - X_cs @ PCs @ PCs.T
        sq_rec_oss = np.power(epsilon_rec, 2)

        #Now compute the distance distribution, and delete the observations in the
        #upper 3% (done in the while loop) to get the outlier-free matrix.

        #Divide the distance vector in 100 bins
        n_bins = 100
        min_interval = np.min(sq_rec_oss)
        max_interval = np.max(sq_rec_oss)

        delta_step = (max_interval - min_interval) / n_bins

        counter = 0
        bin_id = np.empty((len(epsilon_rec),))
        var_left = min_interval

        #Find the observations in each bin (find the idx, where the classes are
        #the different bins number)
        while counter <= n_bins:
            var_right = var_left + delta_step
            mask = np.logical_and(sq_rec_oss >= var_left, sq_rec_oss < var_right)
            bin_id[np.where(mask)[0]] = counter
            counter += 1
            var_left += delta_step

        #Compute the classes (unique) and the number of elements per class (counts)
        unique,counts=np.unique(bin_id,return_counts=True)
        #Declare the variables to build the CDF to select the observations belonging to the
        #98% of the total
        cumulativeDensity = 0
        new_counter = 0

        while cumulativeDensity < 0.98:
            cumulative_ = counts[new_counter]/self.X.shape[0]
            cumulativeDensity += cumulative_
            new_counter += 1

        new_mask = np.where(bin_id > new_counter)
        self.X = np.delete(self.X, new_mask, axis=0)

        return self.X, bin_id, new_mask


    def outlier_removal_multistep(self):
        '''
        Parente, Alessandro, and James C. Sutherland. Combustion and flame 160.2 (2013): 340-350.


        This function has not been tested yet, but it's running correctly.
        '''

        from scipy.stats import kurtosis

        convergence = False
        iterations = 0
        kurtosis_ = 1
        conv_tol = 1E-6
        iterMax = 150
        TOL = 1E-16

        while not convergence:
            #Trim the input data to have a robust Mahalanobis distance, after PCA
            input_eigens = self.eigens
            self.eigens = self.X.shape[1]-1

            PCs, eigval = self.fit()
            scores = self.get_scores()
            mahalanobis_ = np.empty((self.X.shape[0],), dtype=float)

            #The observations associated with large values of DM (mahal) are classified as outliers
            #and then discarded
            for ii in range(0,self.X.shape[0]):
                t_sq = 0
                lam_j = 0
                for jj in range(0, self.X.shape[1]-1):
                    t_sq += scores[ii,jj]**2
                    lam_j += eigval[jj]
                mahalanobis_[ii] = t_sq/(lam_j + TOL)

            #A fraction alpha (typically 0.01%-0.1%) of the data points characterized by the largest
            #value of DM are classified as outliers and removed.
            if iterations < 20:
                alpha = 0.000007
            else:
                alpha = 0

            #compute the new number of observations after the trim factor:
            trim = int((1-alpha)*self.X.shape[0])
            to_trim = np.argsort(mahalanobis_)

            new_mask = to_trim[:trim]
            self.X = self.X[new_mask,:]

            print("X trimmed dim: {}".format(self.X.shape))

            #Compute the PCA scores. Override the eventual number of PCs: ALL the
            #PCs are needed, as the outliers are also given by the last PCs examination
            PCs, eigval = self.fit()
            scores = self.get_scores()
            w_scores = scores/np.sqrt(eigval)
            #Select as "important" the PCs which explain the 20% of the average eigenvalue
            self.eigens = input_eigens


            #compute the curtosis of the new w_scores = u_scores/sqrt(eigenvalues)
            new_kurt = np.mean(kurtosis(w_scores[:,:self.eigens]))
            #check if the kurtosis variation is below the fixed threshold, to activate convergence
            check_conv = (new_kurt - np.mean(kurtosis_))/(new_kurt + TOL)
            print("Delta Kurtosis: {}".format(check_conv))

            if check_conv <= conv_tol or iterations >= iterMax:
                convergence = True
                break

            mahalanobis_ = np.empty((self.X.shape[0],), dtype=float)
            scores_dist = np.empty((self.X.shape[0],), dtype=float)
            #Compute again the Mahalanobis distance for the robust set of scores, evaluating the
            #important PCs
            for ii in range(0,self.X.shape[0]):
                t_sq = 0
                lam_j = 0
                for jj in range(0, self.eigens):
                    t_sq += scores[ii,jj]**2
                    lam_j += eigval[jj]
                mahalanobis_[ii] = t_sq/(lam_j + TOL)
            #remove the points in the 99th quantile
            to_remove = np.quantile(mahalanobis_, 0.9995)
            new_mask = np.where(mahalanobis_ > to_remove)

            #Do the same, but on the very last PCs.
            r = len(np.where(eigval < 0.2*np.mean(eigval))[0])

            for ii in range(0,self.X.shape[0]):
                t_sq = 0
                lam_j = 0
                for jj in range(scores.shape[1]-r+1, scores.shape[1]):
                    t_sq += scores[ii,jj]**2
                    lam_j += eigval[jj]
                scores_dist[ii] = t_sq/(lam_j + TOL)
            #remove also here the scores in the 99th quantile
            to_remove2 = np.quantile(scores_dist, 0.9995)
            new_mask2 = np.where(scores_dist >= to_remove2)
            #merge the idx of the points which were selected in the two steps, and delete
            #the repetitions (unique)
            temp = np.concatenate((new_mask, new_mask2), axis=1)
            to_delete = np.unique(temp)

            print('Observations to delete: {}'.format(len(to_delete)))
            #Delete the points from the matrix
            self.X = np.delete(self.X, to_delete, axis=0)

            print("Iteration number: {}".format(iterations))
            iterations +=1
            #store the "previous" Kurtosis
            kurtosis_ = kurtosis(w_scores[:,:self.eigens])


            print("The training matrix dimensions without outliers are: {}x{}".format(self.X.shape[0], self.X.shape[1]))


        return self.X


class LPCA(PCA):
    def __init__(self,X):
        #Set the path where the file 'idx.txt' (containing the partitioning solution) is located
        self._path_to_idx = 'path'
        #Set the PC number to plot or the variable's number to plot
        self._num_to_plot = 1
        #Set the cluster number where plot the PC
        self._clust_to_plot = 1

        super().__init__(X)

    @property
    def path_to_idx(self):
        return self._path_to_idx

    @path_to_idx.setter
    def path_to_idx(self, new_string):
        self._path_to_idx = new_string

    @property
    def clust_to_plot(self):
        return self._clust_to_plot

    @clust_to_plot.setter
    @accepts(object, int)
    def clust_to_plot(self, new_number):
        self._clust_to_plot = new_number

    @staticmethod
    def get_idx(path):

        try:
            print("Reading idx..")
            idx = np.genfromtxt(path + '/idx.txt', delimiter= ',')
        except OSError:
            print("Could not open/read the selected file: " + path + 'idx.txt')
            exit()

        return idx


    def fit(self):
        '''
        This function computes the LPCs (Local Principal Components), the u_scores
        (the projection of the points on the local manifold), and the eigenvalues
        in each cluster found by the lpca iterative algorithm, given a previous clustering
        solution.

        - Output:
        LPCs = list with the LPCs in each cluster -- dim: [k]
        u_scores = list with the scores in each cluster -- dim: [k]
        Leigen = list with the eigenvalues in each cluster -- dim: [k]
        centroids = list with the centroids in each cluster -- dim: [k]
        '''
        self.idx = self.get_idx(self.path_to_idx)
        self.k = int(max(self.idx) +1)
        self.X_tilde = self.preprocess_training(self.X, self.to_center, self.to_scale, self.centering, self.scaling)


        self.centroids = [None] *self.k
        self.LPCs = [None] *self.k
        self.u_scores = [None] *self.k
        self.Leigen = [None] *self.k

        for ii in range (0,self.k):
            cluster = get_cluster(self.X_tilde, self.idx, ii)
            self.centroids[ii], cluster_ = center(cluster, self._centering, True)
            self.LPCs[ii], self.Leigen[ii] = PCA_fit(cluster_, self._nPCs)
            self.u_scores[ii] = cluster_ @ self.LPCs[ii]

        return self.LPCs, self.u_scores, self.Leigen, self.centroids


    def recover(self):
        '''
        Reconstruct the original matrix from the 'k' local reduced PCA-manifolds.
        Given the idx vector, for each cluster the points are reconstructed from the
        local manifolds spanned by the local PCs.

        - Input:
        X = UNCENTERED/UNSCALED data matrix -- dim: (observations x variables)
        idx = class membership vector -- dim: (obs x 1)
        modes = set of eigenvectors (PCs) -- dim: (num_PCs x variables)
        cent_crit = centering criterion for the X matrix (MEAN or MIN)
        scal_crit = scaling criterion for the X matrix (AUTO, RANGE, VAST, PARETO)
        - Output:
        X_rec = uncentered and unscaled reconstructed matrix with LPCA modes -- dim: (observations x variables)
        '''


        self.X_rec = np.empty(self.X.shape, dtype=float)
        self.X_tilde = self.preprocess_training(self.X, self.to_center, self.to_scale, self.centering, self.scaling)

        mu_global = center(self.X, self.centering)
        sigma_global = scale(self.X, self.scaling)


        self.LPCs, self.u_scores, self.Leigen, self.centroids = self.fit()


        for ii in range (0,self.k):
            cluster_ = get_cluster(self.X_tilde, self.idx, ii)
            centroid_ =self.centroids[ii]
            C = np.empty(cluster_.shape, dtype=float)
            C = (cluster_ - centroid_) @ self.LPCs[ii] @ self.LPCs[ii].T
            C_ = uncenter(C, centroid_)
            positions = np.where(self.idx == ii)
            self.X_rec[positions] = C_

        self.X_rec = unscale(self.X_rec, sigma_global)
        self.X_rec = uncenter(self.X_rec, mu_global)

        return self.X_rec


    def plot_parity(self):
        '''
        Print the parity plot of the reconstructed profile from the PCA
        manifold. The more the scatter plot (black dots) is in line with the
        red line, the better it is the reconstruction.
        '''

        reconstructed_ = self.recover()

        matplotlib.rcParams.update({'font.size' : 18, 'text.usetex' : True})
        fig = plt.figure()
        axes = fig.add_axes([0.15,0.15,0.7,0.7], frameon=True)
        axes.plot(self.X[:,self._num_to_plot], self.X[:,self._num_to_plot], color='r', linestyle='-', linewidth=2, markerfacecolor='b')
        axes.scatter(self.X[:,self._num_to_plot], reconstructed_[:,self._num_to_plot], 1, color= 'k')
        axes.set_xlabel('Original variable')
        axes.set_ylabel('Reconstructed from LPCA manifold')
        plt.xlim(min(self.X[:,self._num_to_plot]), max(self.X[:,self._num_to_plot]))
        plt.ylim(min(self.X[:,self._num_to_plot]), max(self.X[:,self._num_to_plot]))
        #axes.set_title('Parity plot')
        plt.show()


    def plot_PCs(self):
        '''
        Plot the variables' weights on a selected Principal Component (PC).
        The PCs are linear combination of the original variables: examining the
        weights, especially for the PCs associated with the largest eigenvalues,
        can be important for data-analysis purposes.
        '''
        local_eigen = self.LPCs[self.clust_to_plot]

        matplotlib.rcParams.update({'font.size' : 18, 'text.usetex' : True})
        fig = plt.figure()
        axes = fig.add_axes([0.15,0.15,0.7,0.7], frameon=True)

        x = np.linspace(1, self.n_var, self.n_var)
        axes.bar(x, local_eigen[:,self.set_num_to_plot])
        axes.set_xlabel('Variables [-]')
        axes.set_ylabel('Weights on the PC number: {}, k = {} [-]'.format(self.set_num_to_plot, self.clust_to_plot))
        plt.show()


class KPCA(PCA):
    def __init__(self, X):

        #Set the sigma - the coefficient for the kernel construction
        self.sigma = 10

        super().__init__(X)


    def fit(self):
        '''
        Compute the Kernel Principal Component Analysis for a dataset X, using
        a gaussian Radial Basis Function (RBF).
        - Input:
        X = CENTERED/SCALED data matrix -- dim: (observations x variables)
        n_eigs = number of principal components to retain -- dim: (scalar)
        sigma = free parameter for the kernel construction, optional -- dim: (scalar)

        WARNING: This method can be extremely expensive for large matrices.
        '''
        from scipy.spatial.distance import pdist, squareform

        self.X_tilde = KPCA.preprocess_training(self.X, self.to_center, self.to_scale, self.centering, self.scaling)

        print("Starting kernel computation..")
        # compute the distances between all the observations:
        distances = pdist(self.X_tilde, 'sqeuclidean')
        square_distances = squareform(distances)

        # build the first kernel, center it with the 1n matrix, then compute the centered kernel K:
        Kernel = np.exp(-sigma * square_distances)
        centering_k = np.ones((n_obs, n_obs))/n_obs
        K = Kernel - centering_k @ Kernel - Kernel @ centering_k + centering_k @ Kernel @ centering_k

        print("Starting kernel decomposition..")
        # Compute the PCs from the kernel matrix, and retain the first 'n_eigs' PCs:
        evals, evecs = LA.eigh(K)
        mask = np.argsort(evals)[::-1]
        evecs = evecs[:,mask]
        evals = evals[mask]
        evecs = evecs[:,:self.eigens]

        return evecs


class variables_selection(PCA):
    '''
    In many applications, rather than reducing the dimensionality considering a new set of coordinates
    which are linear combination of the original ones, the main interest is to achieve a dimensionality
    reduction selecting a subset of m variables from the original set of p variables.
    This can be done via PCA, as also explained in [a].
    Three methods for variables selection are implemented in this class:
    i) Method B2 backward;
    ii) Method B4 forward;
    iii) Variables selection via PCA and Procustes Analysis, by means of the Krzanovski iterative algorithm [b]

    Additional info about the methods are available in the fit method.


    WARNING --> the input matrix must be the original (uncentered, unscaled) one. The code centers and scales
                automatically.

    '''
    def __init__(self, X, *dictionary):
        self.X = X


        #Initialize the number of variables to select and the PCs to retain

        self._n_ret = 1
        self._path = ' '
        self._labels_name = ' '

        super().__init__(self.X)

        self._method = 'B2' #'B2', 'B4', "Procustes", "procustes_rotation"

        if dictionary:
            settings = dictionary[0]

            self._nPCs = settings["number_of_PCs"]
            self._method = settings["method"]
            self._center = settings["center"]
            self._centering = settings["centering_method"]
            self._scale = settings["scale"]
            self._scaling = settings["scaling_method"]
            self._n_ret = settings["number_of_variables"]
            self._path = settings["path_to_labels"]
            self._labels_name = settings["labels_name"]


    @property
    def retained(self):
        return self._n_ret

    @retained.setter
    @accepts(object, int)
    def retained(self, new_number):
        self._n_ret = new_number

        if self._n_ret <= 0:
            raise Exception("The number of retained variables must be a positive integer. Exiting..")
            exit()

    @property
    def path_to_labels(self):
        return self._path

    @path_to_labels.setter
    def path_to_labels(self, new_string):
        self._path = new_string


    @property
    def labels_file_name(self):
        return self._labels_name

    @labels_file_name.setter
    def labels_file_name(self, new_string):
        self._labels_name = new_string

    @property
    def method(self):
        return self._method

    @method.setter
    def method(self, new_string):
        self._method = new_string


    def load_labels(self):
        import pandas as pd
        try:
            self.labels= np.array(pd.read_csv(self._path + '/' + self._labels_name, sep = ',', header = None))
        except OSError:
            print("Could not open/read the selected file: " + self._labels_name)
            exit()


    @staticmethod
    def check_sanity_input(X, labels, retained):
        #print(labels)
        if X.shape[1] != len(labels):
            print("Variables number: {}, Labels length: {}".format(X.shape[1], labels.shape[1]))
            raise Exception("The number of variables does not match the labels.")
            exit()
        elif retained >= X.shape[1]:
            raise Exception("The number of retained variables must be lower than the number of original variables.")
            exit()


    def fit(self):
        print("Selecting global variables via PCA and Procustes Analysis...")
        self.load_labels()
        variables_selection.check_sanity_input(self.X, self.labels, self._n_ret)

        self.X_tilde = PCA.preprocess_training(self.X, self.to_center, self.to_scale, self.centering, self.scaling)

        if self._method.lower() == 'procustes':
            '''
            The iterative variable algorithm introduced by Krzanovski [a] is based on the following steps (1-3):
            0.  Preprocessing: The training matrix X is centered and scaled, after being loaded.
            1.  The dimensionality of m is initially set equal to p.
            2.  Each variable is deleted from the matrix X, obtaining p ~X matrices. The
                corresponding scores matrices are computed by means of PCA. For each of them, a Procustes Analysis
                is performed with respect to the scores of the original matrix X, and the corresponding M2 coeffcient is computed.
            3.  The variable which, once excluded, leads to the smallest M2 coefficient is deleted from the matrix.
            4.  Steps 2 and 3 are repeated until m variables are left.
            '''
            #Start with PCA, and compute the scores (Z)
            eigenvec = PCA_fit(self.X_tilde, self._nPCs)
            Z = self.X_tilde @ eigenvec[0]
            #Start the backward elimination:
            while self.X_tilde.shape[1] > self._n_ret:
                M2 = 1E12
                M2_tmp = 0
                var_tmp = 0

                for ii in range(0,self.X_tilde.shape[1]):
                    #Delete each variable from the original matrix (one at the time)
                    X_cut = np.delete(self.X_tilde, ii, axis=1)
                    #Compute the scores of the reduced matrix, after PCA
                    eigenvec = PCA_fit(X_cut, self._nPCs)
                    Z_tilde = X_cut @ eigenvec[0]
                    #Compute the reduced scores covariance matrix, and then apply SVD
                    covZZ = np.transpose(Z_tilde) @ Z
                    u, s, vh = np.linalg.svd(covZZ, full_matrices=True)
                    #Compute the Procustes Analysis score M2 for the matrix without the 'ii' variable
                    M2_tmp = np.trace((np.transpose(Z) @ Z) + (np.transpose(Z_tilde) @ Z_tilde) - 2*s)
                    #If the Silhouette score M2 is lower than the previous one in M2_tmp, store the
                    #variable 'ii' to remove it after the for loop
                    if M2_tmp < M2:
                        M2 = M2_tmp
                        var_tmp = ii
                #Remove the variable from the matrix and the labels list
                self.X_tilde = np.delete(self.X_tilde, var_tmp, axis=1)
                self.labels = np.delete(self.labels, var_tmp, axis=0)
                print("Current number of variables: {}".format(self.X_tilde.shape[1]))

            return self.labels

        elif self._method.lower() == 'b2':
            '''
            The variable with the largest weight is found on the last PC, and then it is deleted.
            This is accomplished via iterative backward elimination algorithm, until the number of
            variables is equal to the selected number of variables.
            '''
            #Number of variables before the elimination starts:
            max_var = self.X.shape[1]
            #While the number of variables is larger than the number you want to retain 'm', go on
            #with the elimination process:
            while max_var > self.retained:
                #Perform PCA:
                model = PCA(self.X)
                model.eigens = self._nPCs
                PCs,eigvals = model.fit()
                #Check which variable has the max weight on the last PC. Python starts to count from
                #zero, that's why the last number is "self._nPCs -1" and not "self._nPCs"
                max_on_last = np.max(np.abs(PCs[:,self._nPCs-1]))
                argmax_on_last = np.max(np.abs(PCs[:,self._nPCs-1]))
                #Delete the selected variable
                self.X_tilde = np.delete(self.X_tilde, argmax_on_last, axis=1)
                self.labels = np.delete(self.labels, argmax_on_last, axis=0)
                print("Current number of variables: {}".format(self.X_tilde.shape[1]))
                #Get the current number of variables for the while loop
                max_var = self.X_tilde.shape[1]


            return self.labels

        if self._method.lower() == 'procustes_rotation':
            '''
            It's basically the same of standard Procustes, but this time the scores
            are rotated via Varimax.
            '''
            #Start with PCA, and compute the scores (Z)
            eigenvec = PCA_fit(self.X_tilde, self._nPCs)
            Z = self.X_tilde @ eigenvec[0]
            #Start the backward elimination:
            while self.X_tilde.shape[1] > self._n_ret:
                M2 = 1E12
                M2_tmp = 0
                var_tmp = 0

                for ii in range(0,self.X_tilde.shape[1]):
                    #Delete each variable from the original matrix (one at the time)
                    X_cut = np.delete(self.X_tilde, ii, axis=1)
                    #Compute the scores of the reduced matrix, after PCA
                    eigenvec = PCA_fit(X_cut, self._nPCs)
                    Z_tilde = X_cut @ eigenvec[0]
                    #ROTATE THE SCORES VIA VARIMAX
                    Z_tilde = varimax_rotation(self.X_tilde, Z_tilde, normalize=True)
                    #Compute the reduced scores covariance matrix, and then apply SVD
                    covZZ = np.transpose(Z_tilde) @ Z
                    u, s, vh = np.linalg.svd(covZZ, full_matrices=True)
                    #Compute the Procustes Analysis score M2 for the matrix without the 'ii' variable
                    M2_tmp = np.trace((np.transpose(Z) @ Z) + (np.transpose(Z_tilde) @ Z_tilde) - 2*s)
                    #If the Silhouette score M2 is lower than the previous one in M2_tmp, store the
                    #variable 'ii' to remove it after the for loop
                    if M2_tmp < M2:
                        M2 = M2_tmp
                        var_tmp = ii
                #Remove the variable from the matrix and the labels list
                self.X_tilde = np.delete(self.X_tilde, var_tmp, axis=1)
                self.labels = np.delete(self.labels, var_tmp, axis=0)
                print("Current number of variables: {}".format(self.X_tilde.shape[1]))

            return self.labels

        elif self._method.lower() == 'b4':

            #The variables associated with the largest weights on each of the 'm' first PCs are
            #selected. This is not an iterative algorithm.

            model = PCA(self.X)
            if self._nPCs < self._n_ret:
                print("For the B4 it is not possible to choose a number of PCs lower than the required number of variables.")
                print("The number of PCs will be set equal to the required number of variables.")
                print(" ")
                self._nPCs = self._n_ret

            model.eigens = self._nPCs
            PCs,eigvals = model.fit()
            PVs = []

            for ii in range(0, self._n_ret):
                #Check the largest weight on the first 'm' PCs and add it to the PVs list.
                argmax_= np.argmax(np.abs(PCs[:,ii]))
                PVs.append(self.labels[argmax_])
                #Set the variable weight to zero on all the PCs, to avoid repetition in the PVs list.
                PCs[argmax_,:]= 0

            return PVs

        else:
            raise Exception("Variables selection method not supported. Please choose one between 'B2', 'Procustes', 'Procustes_rotation'.")
            print("Exiting with error..")
            exit()



class SamplePopulation():
    '''
    This class contains a set of methods to consider only a subset of the original training
    matrix X. These methods should be used when the size of the training dataset is large, and
    becomes impractical to train the model on the whole training population.
    Three classes of sampling strategies are available:
    i) Simple random sampling; ii) Clustered sampling; iii) Stratified sampling; iv) multistage.
    The 'clustered' sampling can be accomplished either via miniBatchKMeans, or LPCA.

    The simple random sampling just shuffle the data and takes the required amount of observations.
    The clustered approach groups the observations in different clusters, and from each of them
    a certain amount of samples are taken.
    The multistage couples stratified (first stage) and clustered (second stage) sampling
    '''
    def __init__(self, X):
        #Initial training dataset (raw data).
        self.X = X
        self.__nObs = self.X.shape[0]
        self.__nVar = self.X.shape[1]
        #Choose the sampling strategy: random, cluster (KMeans, LPCA), stratifed or multistage.
        self._method = 'KMeans'
        self.__condVec = False
        #Choose the dimensions of the sampled dataset.
        self._dimensions = 1
        #Predefined number of clusters, if 'cluster', 'stratified' or 'multistage' are chosen
        self.__k = 32
        #Variable to use for the matrix conditioning in case of stratified sampling
        self._conditioning =0

    @property
    def sampling_strategy(self):
        return self._method

    @sampling_strategy.setter
    def sampling_strategy(self, new_string):
        self._method = new_string

    @property
    def set_size(self):
        return self._dimensions

    @set_size.setter
    def set_size(self, new_value):
        self._dimensions = new_value

    @property
    def set_conditioning(self):
        return self._conditioning

    @set_conditioning.setter
    def set_conditioning(self, new_value):
        self._conditioning = new_value
        if not isinstance(self._conditioning, int) and  not isinstance(self._conditioning, float):
            self._conditioning = new_value
            self.__condVec = True

    def fit(self):
            #Center and scale the matrix (auto preset)
            self.X_tilde = center_scale(self.X, center(self.X,'mean'), scale(self.X, 'auto'))
            self.__batchSize = int(self._dimensions / self.__k)

            if self._method == 'random':
                #Randomly shuffle the observations and take the prescribed number
                np.random.shuffle(self.X)
                miniX = self.X[:self.__batchSize,:]
            elif self._method == 'KMeans':
                #Perform KMeans and take (randomly) from each cluster a certain
                #batch to form the sampled matrix.
                model_KM = clustering.KMeans(self.X_tilde)
                model_KM.clusters = self.__k
                model_KM.initMode = True
                id = model_KM.fit()
                miniX = self.X[1:3,:]
                for ii in range(0, max(id)+1):
                    cluster_ = get_cluster(self.X, id, ii)
                    #If the cluster contains less observation than the batch
                    #size, then take all the clusters' observations.
                    if cluster_.shape[0] < self.__batchSize:
                        miniX = np.concatenate((miniX, cluster_), axis=0)
                    else:
                        #Otherwise, shuffle the cluster and take the first
                        #batchsize observations.
                        np.random.shuffle(cluster_)
                        miniX = np.concatenate((miniX, cluster_[:self.__batchSize,:]), axis=0)
                        if miniX.shape[0] < self._dimensions and ii == max(id):
                            delta = self._dimensions - miniX.shape[0]
                            miniX= np.concatenate((miniX, cluster_[(self.__batchSize+1):(self.__batchSize+1+delta),:]), axis=0)
            elif self._method == 'LPCA':
                #Do the exact same thing done in KMeans, but using the LPCA
                #clustering algorithm. The number of PCs is automatically
                #assessed via explained variance. The number of LPCs is chosen
                #as LPCs = PCs/2
                global_model = PCA(self.X)
                optimalPCs = global_model.set_PCs()
                model = clustering.lpca(self.X_tilde)
                model.clusters = self.__k
                model.eigens = int(optimalPCs / 2)
                id = model.fit()
                miniX = self.X[1:3,:]
                for ii in range(0, max(id)+1):
                    cluster_ = get_cluster(self.X, id, ii)
                    if cluster_.shape[0] < self.__batchSize:
                        miniX = np.concatenate((miniX, cluster_), axis=0)
                    else:
                        np.random.shuffle(cluster_)
                        miniX = np.concatenate((miniX, cluster_[:self.__batchSize,:]), axis=0)
                        if miniX.shape[0] < self._dimensions and ii == max(id):
                            delta = self._dimensions - miniX.shape[0]
                            miniX= np.concatenate((miniX, cluster_[(self.__batchSize+1):(self.__batchSize+1+delta),:]), axis=0)
            elif self._method == 'stratified':
                #Condition the dataset dividing the interval of one variable in
                #'k' bins and sample from each bin. The default variable to
                #condition with is '0'. This setting must be eventually modified
                #via setter.
                if not self.__condVec:
                    min_con = np.min(self.X[:,self._conditioning])
                    max_con = np.max(self.X[:,self._conditioning])
                else:
                    min_con = np.min(self._conditioning)
                    max_con = np.max(self._conditioning)
                #Compute the extension of each bin (delta_step)
                self.__kHardConditioning = 100
                delta_step = ((max_con - min_con) / self.__kHardConditioning)
                counter = 0
                var_left = min_con
                miniX = self.X[1:3,:]
                while counter <= self.__kHardConditioning:
                    #Compute the two extremes, and take all the observations in
                    #the dataset which lie in the interval.
                    var_right = var_left + delta_step
                    if not self.__condVec:
                        mask = np.logical_and(self.X[:,self._conditioning] >= var_left, self.X[:,self._conditioning] < var_right)
                    else:
                        mask = np.logical_and(self._conditioning >= var_left, self._conditioning < var_right)
                    cluster_ = self.X[mask]
                    #Also in this case, if the cluster size is lower than the
                    #batch size, take all the cluster.
                    if cluster_.shape[0] < self.__batchSize:
                        miniX = np.concatenate((miniX, cluster_), axis=0)
                        var_left += delta_step
                        counter+=1
                    else:
                        np.random.shuffle(cluster_)
                        miniX = np.concatenate((miniX, cluster_[:self.__batchSize,:]), axis=0)
                        if miniX.shape[0] < self._dimensions and counter == self.__kHardConditioning:
                            delta = self._dimensions - miniX.shape[0]
                            miniX= np.concatenate((miniX, cluster_[(self.__batchSize+1):(self.__batchSize+1+delta),:]), axis=0)
                        var_left += delta_step
                        counter+=1
            elif self._method == 'multistage':
                #Stratified sampling step: build multiMiniX from X conditioning,
                #and after that cluster to have a further reduction in the
                #dataset' size. The conditioning is done with k = 32, while the
                #clustering takes k = 16
                self.__multiBatchSize = 2*self.__batchSize
                self.__kHardConditioning = 100
                if not self.__condVec:
                    min_con = np.min(self.X[:,self._conditioning])
                    max_con = np.max(self.X[:,self._conditioning])
                else:
                    min_con = np.min(self._conditioning)
                    max_con = np.max(self._conditioning)
                delta_step = ((max_con - min_con) / self.__kHardConditioning)
                counter = 0
                var_left = min_con
                multiMiniX = self.X[1:3,:]
                while counter <= self.__kHardConditioning:
                    var_right = var_left + delta_step
                    if not self.__condVec:
                        mask = np.logical_and(self.X[:,self._conditioning] >= var_left, self.X[:,self._conditioning] < var_right)
                    else:
                        mask = np.logical_and(self._conditioning >= var_left, self._conditioning < var_right)
                    cluster_ = self.X[mask]
                    if cluster_.shape[0] < self.__multiBatchSize:
                        multiMiniX = np.concatenate((multiMiniX, cluster_), axis=0)
                        var_left += delta_step
                        counter+=1
                    else:
                        np.random.shuffle(cluster_)
                        multiMiniX = np.concatenate((multiMiniX, cluster_[:self.__multiBatchSize,:]), axis=0)
                        if multiMiniX.shape[0] < self._dimensions and counter == self.__kHardConditioning:
                            delta = self._dimensions - multiMiniX.shape[0]
                            multiMiniX= np.concatenate((multiMiniX, cluster_[(self.__multiBatchSize+1):(self.__multiBatchSize+1+delta),:]), axis=0)
                        var_left += delta_step
                        counter+=1
                #Clustering sampling step: build miniX from multiMiniX via KMeans
                multiMiniX_tilde = center_scale(multiMiniX, center(multiMiniX,'mean'), scale(multiMiniX, 'auto'))
                multiK = int(self.__k / 2)
                miniX = self.X[1:3,:]
                model_KM = clustering.KMeans(multiMiniX_tilde)
                model_KM.clusters = self.__k
                model_KM.initMode = True
                id = model_KM.fit()
                for ii in range(0, max(id)+1):
                    cluster_ = get_cluster(multiMiniX, id, ii)
                    if cluster_.shape[0] < self.__batchSize:
                        miniX = np.concatenate((miniX, cluster_), axis=0)
                    else:
                        np.random.shuffle(cluster_)
                        miniX = np.concatenate((miniX, cluster_[:self.__batchSize,:]), axis=0)
                        if miniX.shape[0] < self._dimensions and ii == max(id):
                            delta = self._dimensions - miniX.shape[0]
                            miniX= np.concatenate((miniX, cluster_[(self.__batchSize+1):(self.__batchSize+1+delta),:]), axis=0)

            #it can happen that few observations are missing to reach the prescribed number of observations of
            #the sampled matrix. In this case, fill the gap with random observations from the training matrix
            if miniX.shape[0] < self._dimensions:
                np.random.shuffle(self.X)
                delta = self._dimensions - miniX.shape[0]

                miniX = np.concatenate((miniX, self.X[:delta,:]), axis=0)


            return miniX

class NMF():
    def __init__(self, X):
        #standard construction
        self.X = X 
        self.rows, self.cols = self.X.shape
        self._dim = self.cols -1

        #tell to the algorithm if the matrix must be centered/scaled.
        #only Range scaling is possible, so no setter for the method 
        #is prescribed.
        self._center = True
        self._scale = True

        #private properties for iterative algorithm
        self.__iterMax = 100
        self.__convergence = False

    @property
    def to_center(self):
        return self._center

    @to_center.setter
    @accepts(object, bool)
    def to_center(self, new_bool):
        self._center = new_bool

    @property
    def to_scale(self):
        return self._scale

    @to_scale.setter
    @accepts(object, bool)
    def to_scale(self, new_bool):
        self._scale = new_bool

    @property
    def encoding(self):
        return self._dim

    @encoding.setter
    @accepts(object, int)
    def encoding(self, new_int):
        self._dim = new_int

    @staticmethod
    def preprocess_training(X, centering_decision, scaling_decision):

        centering_method = 'min'
        scaling_method = 'range'

        if centering_decision and scaling_decision:
            mu, X_ = center(X, centering_method, True)
            sigma, X_tilde = scale(X_, scaling_method, True)
        elif centering_decision and not scaling_decision:
            mu, X_tilde = center(X, centering_method, True)
        elif scaling_decision and not centering_decision:
            sigma, X_tilde = scale(X, scaling_method, True)
        else:
            X_tilde = X

        return X_tilde

    def fit(self):
        '''
        The alternating least squares algorithm has been implemented in this function.
        The algorithm description and general NMF infos can be found here:

        https://www.mpi-inf.mpg.de/fileadmin/inf/d5/teaching/ss15_dmm/lectures/2015-05-26-intro-to-nmf.pdf
        '''

        from numpy.linalg import lstsq

        #Center and scale the matrix. The only criterion is Range, because the matrix elements
        #must be all positive
        self.X_tilde = self.preprocess_training(self.X, self._center, self._scale)

        #Initialize matrices for low-rank approximation
        self.W = np.random.rand(self._dim, self.rows)
        self.H = np.random.rand(self._dim, self.cols)

        #Initialize the param for the iterative algorithm
        iteration = 0
        eps_rec = 1.0
        convTol = 1E-8
        eps_tol = 1E-16

        while not self.__convergence and iteration < self.__iterMax:
            
            #optimize H, and after that delete negative coefficients
            self.H = lstsq(self.W.T, self.X_tilde, rcond=None)[0]
            mask = np.where(self.H < 0)
            self.H[mask] = 0

            #optimize W, and after that delete negative coefficients
            self.W = lstsq(self.H.T, self.X_tilde.T, rcond=None)[0]
            mask = np.where(self.W < 0)
            self.W[mask] = 0

            #Compute the reconstructed matrix from the reduced-order basis
            X_rec = self.W.T @ self.H

            #Compute the error between the original and the reconstructed
            #via Frobenius norm
            eps_rec_new = np.linalg.norm((self.X_tilde - X_rec), 'fro')

            #Check the reconstruction error variation to see if the convergence
            #has been reached
            eps_rec_var = np.abs((eps_rec_new - eps_rec) / (eps_rec_new) + eps_tol)
            eps_rec = eps_rec_new

            if eps_rec_var > convTol and iteration < self.__iterMax:
                print("Iteration number: {}".format(iteration))
                print("\tReconstruction error variance: {}".format(eps_rec_var))
                iteration +=1
            else:
                print("Convergence has been reached after {} iterations.".format(iteration))

        return self.W, self.H