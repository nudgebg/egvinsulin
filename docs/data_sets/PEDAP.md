# PEDAP 
This page summarizes our insights about the clinical study data of the **PEDAP** study in efforts to understand how to handle bolus, basal, and cgm data, list assumptions that were made, and pose open questions. 

- **Study Name**: The Pediatric Artificial Pancreas (PEDAP) trial: A Randomized Controlled Comparison of the Control- IQ technology Versus Standard of Care in Young Children in Type 1 Diabetes
- **Description**: The objective of the study was to assess efficacy, quality of life, and safety of a closed loop control (CLC) system (t:slim X2 with Control-IQ Technology) in a randomized controlled trial with partial crossover.  
- **Devices**: t:slim X2 with Control-IQ and Dexcom G6 system
- **Study Population**: Children aged 2 - 5 years old



## History


| Analysis| Date| Notes|
|----------|------------|----|
| `notebooks/understand-pedap-dataset.ipynb` | - | Original analysis of the dataset `PEDAP Public Dataset - Release 3 - 2024-09-25.zip`.|
| `2025-04-07 - PEDAP Missing Basal.ipynb`   | 2025-04-07 | We noticed missing basal data in the current study dataset and reached out to JAEB.|
| -| 2025-04-16 | JAEB released an updated version of the PEDAP study `PEDAP Public Dataset - Release 4 - 2025-04-10.zip`| 
|`2025-04-16 - understand-new-pedap-basal-format.ipynb`| Analysis of new basal file.|


### Study releases
| Release (Study File Name)                                       | Note                      | 
| --------------------------------------------- | ------------------------------ |
| PEDAP Public Dataset - Release 3 - 2024-09-25.zip | `PEDAPTandemBASALRATECHG.txt` 44 MB Basal file contained only first 13 days of data for CLC group.|
| PEDAP Public Dataset - Release 4 - 2025-04-10.zip | `PEDAPTandemBASALDELIVERY.txt` After request to JAEB, 257 MB basal file was added proving much more basal data|
|                                               |                                |


### Relevant Data Tables

From the DataGlossary.rtf file, the following relevant files were identified which are stored in the **Data Files** subfolder.

* **PEDAPTandemBOLUSDELIVERED**.txt: Event logged on pump when delivery of an insulin bolus (Standard, Extended, or Automatic) is completed
* **PEDAPTandemBASALDELIVERY.txt** ~~PEDAPTandemBASALRATECHG.txt~~ (see [releases](#study-releases)): Event logged on pump when insulin basal rate changes due to pumping events
* **PEDAPTandemCGMDataGXB.txt**: List of cgm data downloaded 
* **PtRoster.txt**: Patient Roster

These are csv files ("|" separator) and host many columns related to the Tandem pump events and the Dexcom cgm. The glossary provides information about each column. Each file contains a limited amount of columns compared to the FLAIR data. Below are **all** of the columns contained in each file

#### PEDAPTandemBOLUSDELIVERED
* **PtID**: Patient ID
* **DeviceDtTm**: Date-time of completion of bolus delivery
* **BolusAmount**: size of completed bolus
* **CarbAmount**: grams of carbs announced to the pump
* **BolusType**: The bolus insulin delivery type [Standard, Extended, Automatic]
* **Duration**: For extended boluses, the requested bolus duration in minutes
* **ExtendedBolusPortion**: Flag distinguishing the immediate (Now) portion of the bolus (if any) from the extended (Later) portion [Now, Later]
#### PEDAPTandemBASALRATECHG
* **PtID**: Patient ID
* **DeviceDtTm**: Date-time of basal rate change
* **BasalRate**: Basal Rate (U/h) - The active basal insulin delivery rate in units per hour
#### PEDAPTandemCGMDataGXB
* **PtID**: Patient ID
* **DeviceDtTm**: Date-time 
* **CGMValue**: Value of CGM reading, in mg/dL; 0 indicates a below-range reading (<40) or above-range reading (>400)
* **HighLowIndicator**: Flag indicating presence of an in-range reading (0), below-range reading (2), or above-range reading (1)

### Differences between PEDAP and DCLP3/5
**Naming:** In `PEDAP`, the basal rate and CGM events are reported in the same way as in `DCLP` studies. However, the column name for the basal rate value is different in `PEDAP`.

**Extended Boluses:** In `PEDAP`, the *extended portion* of the bolus is reported **at the completion** of the bolus along with how long it was extended for. In `DCLP`, we have to make assumptions on how long the bolus is extended for, and if the extended portion is reported at the announcement or at the completion. 

## Observations

- some mismatching counts for boluses (some nan values?) --> inspect

## Datetime Handling
As in `Flair`, the reported datetime strings miss the time component at midnight. Therefore, automatic parsing is slow. We therefore split the dataset in those with and without datetime strings and then parse the datetimestrings using two different datetime prototypes:

```python
only_date = dates.apply(len) <=10
dates.loc[only_date] = pd.to_datetime(dates.loc[only_date], format='%m/%d/%Y')
dates.loc[~only_date] = pd.to_datetime(dates.loc[~only_date], format='%m/%d/%Y %I:%M:%S %p')
```

## Duplicates & Missing Data
- We see that there are many duplicated data rows (75139 in basal, 677 in cgm, 0 in bolus) without additional information. These are removed. 
- For 3 bolus rows, DateTime data is missing, these are removed

### Drop Non-Tandem Patients (No Basal data)
~~We noticed that the number of unique patient ids between datasets varied. We found that only 65 out of 99 patients have *basal* data. Review of the study protocol showed that this is because basal rate changes are only recorded for CLC (Tandem Control IQ) users while Standard Care (SC) group either is on MDI or a different pump system. We don't have information about the actual basal rates for these patients except for the screening form. Therefore, we only kept patient ids with data in all three datasets.~~
We perviously assumed that SC group has no basal data. This was because the release 3 of the dataset did not contain basal data after week 13 which is why we had to drop all SC patients. However, we later noticed that also CLC patients were missing basal data after week 13. This data was originally missing and was added in release 4 of the dataset (see [release](#study-releases)). 
In the new release 4 the complete basal data is available. This includes basal data for SC patients after week 13. We originally did not notice that the study had SC patients switch to Tandem devices after week 13. 

In summary , both SC and CLC patients used the tandem devices and come with basal bolus and cgm data recorded on the Tandem pump. REgions where SC patients were doing standard care should be excluded, here we don't know what their true basal rates and injections were.

## Extended Boluses
* ~6.5% extended boluses
* Extended boluses can be dual wave or only have an extended bolus (data glossary)
* A dual wave bolus is split in two rows: 
  * Immediate part (ExtendedBolusPortion == `Now`).
  * Extended part (ExtendedBolusPortion == `Later`). Reported upon completion. 
* The duration is repeated in both the `Now` and `Later` rows. Therefore the start of the extended portion must be calculated by subtracting the duration from the timestamp or by taking the timestamp off the immediate part.
* There are `171` more `Later` parts, these *orphans* are assumed to be *non dual wave boluses*: Just an extended part without immediate delivery.

As per the data glossary, the bolus value represents the *completed* delivery and we can therefore safely assume that *extended* boluses are always reported upon completion (even if they don't have an immediate part). This allows us to calculate the *extended* bolus delivery start by subtracting the duration off of the timestamp. 

``` python
df_bolus.DeviceDtTm - pd.to_timedelta(df_bolus.Duration, unit='m')
```

In summary extracting bolus events is an easy task:
 - Removal of rows without timestamp
 - Subtract the duration (0 for standard boluses, >0 for extended portions) from the timestamp to obtain the delivery start time. 

## Basal Rates
### Update 2025-04-17
We noticed missing basal date in the release 3 of the pedap study. After reaching out to JAEB, this resulted in an updated release 4 (see [releases](#study-releases)) with a complete basal file. which is named `PEDAPTandemBASALDELIVERY.txt`. 

We found that 
  1. there are a lot of identical duplicates that need to be dropped. 
    - Most are equal in datetime and rate (75139), 68 differ have same time with different rates (here we use maximum value)
  2. there are a lot of repetitive values (e.g. same, unchanged basal rate reported several times over time) which should be dropped to reduce overhead
  3. In the updated Release 4, the  Standard Care (SC) group also comes with basal data. This is because the SC group (or some of the patients) uses the tandem device after week 13.

### Original Analysis
From the data glossary it was not clear if basal rate events only represent changes from the standard basal rate or changes to the basal rate. To verify, we took a look at the structually very similar `DCLP3` dataset which also comes with a `InsulinPumpSettings_a` file that contians the standard basal rates. We then checked if the PumpBasalRateChange events are reported when standard basal rate change. Visually we could confirm that basal rate changes are reported when standard basal rate changes (overlapping darker scatter points).

In summary, ~~`PEDAPTandemBASALRATECHG.txt`~~ `PEDAPTandemBASALDELIVERY.txt` should contain all basal rate change events.

`


### CGM Special Values
From the data glossary we know that 0 cgm values are either below or above range based on the `HighLowIndicator`:
>0 = CGMValue contains the glucose reading  
>1 = The glucose reading is high~ CGMValue set to 0  
>2 = The glucose reading is low~ CGMValue set to 0

We decided that replacing CGM value with the respective measurement range boundary makes most sense for now but other ways to extrapolate, or introduce special flags, could be employed later on.

```python
df_cgm.loc[i_zero, 'cgm'] = df_cgm.HighLowIndicator.loc[i_zero].replace({ 2: 40, 1: 400 })
```