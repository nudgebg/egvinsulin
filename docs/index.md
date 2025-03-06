# BabelBetes
The BabelBetes project aims to standardize publicly available clinical trial data on continuous glucose monitoring (CGM) and insulin pump delivery, reducing the costs and time associated with data translation for researchers. Motivated by the challenges of inconsistent data formats, BabelBetes will streamline access to usable datasets, accelerating innovation in type 1 diabetes care.​

### Challenges with Publicly Available Clinical Trial Data
Data is the raw material from which models are developed, simulations are composed, and new therapies to reduce the burden of living with type 1 diabetes are developed.

Clinical trials performed at great time and expense, funded by Breakthrough T1D, HCT, and NIH have provided large volumes of granular data which is often stored publicly (www.jaeb.org) or otherwise readily accessible (OPEN Project, OpenAPS, Nightscout Data Commons).

Unfortunately this is often the only data available to researchers and developers seeking to provide innovative solutions for people with type 1 diabetes, putting them at great disadvantage relative to leading medical device companies who together gather more data per day than exists in the entire public domain, ever (approximately 500,000 subject-days).

To add to this, public available data is not stored with consistent methods or formats, resulting in a confusing array of file formats and data descriptors which must be translated at great effort and with high probability of error by each and every researcher or developer hoping to gain insights.

### Last Mile Problem
Babelbetes addresses this “last mile” problem by developing a publicly available set of tools to normalize the clinical trial data hosted at www.jaeb.org, focusing on continuous glucose monitoring and insulin pump delivery. Babelbetes also provides  recommendations on a normalized data set format to ensure future activities provide shovel-ready data for researchers and developers.

### CGM and Insulin First
Our initial focus on datasets containing CGM and insulin delivery data is essential because these are the most valuable data for researchers and developers. Curating device-specific data would yield overly specialized datasets, and normalizing such varied information to create a larger, cohesive dataset would be counterproductive. 

Expanding the scope to include non-insulin / non-cgm data introduces significant variation, making normalization a challenge and complicating the task of identifying common data intersections. Furthermore, different devices may have unique characteristics that cannot be normalized, resulting in fragmented data. Simplifying and normalizing datasets by reducing information is crucial for making the data more useful. 

Including extensive variations and metadata would lead us back to the initial complexity we aimed to avoid.

We also leave post-processing of the normalized cgm, basal, and bolus data to the user, as this requires assumptions which we could not make.  For instance cgm data contains gaps and non-phsyiologic motifs.  Researchers hoping to gain insights on overall cgm data might therefore develop methods for detecting and remediating these events, based on assumptions.

### Conclusion
By implementing this approach to normalize www.jaeb.org’s cgm and insulin pump data, this project minimizes the time and effort required by researchers and developers to utilize clinical trial data, thereby accelerating the development of innovative solutions for managing type 1 diabetes.

## Acknowledgements
Thank you Lane, Rachel, Jan
