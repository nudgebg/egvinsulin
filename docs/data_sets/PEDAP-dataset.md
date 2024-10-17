### The PEDAP study

**Title**: The Pediatric Artificial Pancreas (PEDAP) trial: A Randomized Controlled Comparison of the Control- IQ technology 
Versus Standard of Care in Young Children in Type 1 Diabetes


**Description**: The objective of the study is to assess efficacy, quality of life, and safety of a closed loop control (CLC) system (t:slim X2 with Control-IQ Technology) in a randomized controlled trial with partial crossover.
    
**Devices**: t:slim X2 with Control-IQ and Dexcom G6 system

**Study Population**: Children aged 2 - 5 years old

### Data Tables

The study data folder is named **PEDAP Public Dataset - Release 1 - 2024-04-16**

From the DataGlossary.rtf file, the following relevant files were identified which are stored in the **Data Files** subfolder.

* **PEDAPTandemBOLUSDELIVERED.txt**: Event logged on pump when delivery of an insulin bolus (Standard, Extended, or Automatic) is completed
* **PEDAPTandemBASALRATECHG.txt**: Event logged on pump when insulin basal rate changes due to pumping events
* **PEDAPTandemCGMDataGXB.txt**: List of cgm data dowloaded 
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

## Datetime Handline 
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
We noticed that the number of unique patient ids between datasets varied. We found that only 65 out of 99 patients have *basal* data. Review of the study protocol showed that this is because basal rate changes are only recorded for CLC (Tandem Control IQ) users while Standard Care (SC) group either is on MDI or a different pump system. We don't have information about the actual basal rates for these patients except for the screening form. Therefore, we only kept patient ids with data in all three datasets.

## Extended Boluses
* ~6.5% extended boluses
* Extended boluses can be dual wave or only have an extended bolus (data glossary)
* A dual wave bolus is split in two rows: 
  * Immediate part (ExtendedBolusPortion == `Now`).
  * Extended part (ExtendedBolusPortion == `Later`). Reported upon completion. 
* The duration is repeated in both the `Now` and `Later` rows. Therefore the start of the extended portion must be calculated by subtracting the duration from the timestamp or by taking the timestamp off the immediate part.
* There are `171` more `Later` parts, these *orphans* are assumed to be *non dual wave boluses*: Just an extended part without immediate delivery.

As per data glossary the bolus value represents the *completed* delivery and we can therefore safely assume that *extended* boluses are always reported upon completion (even if they don't have an immediate part). This allows us to calculate the *extended* bolus delivery start by subtracting the duration off of the timestamp. 

``` python
df_bolus.DeviceDtTm - pd.to_timedelta(df_bolus.Duration, unit='m')
```

In summary extracint bolus events is an easy task:
 - Removal of rows without timestamp
 - Subtract the duration (0 for standard boluses, >0 for extended portions) from the timestamp to obtain the delivery start time. 

## Basal Rates
From the data glossary it was not clear if basal rate events only represent changes off of the standard basal rate or all changes to the basal rate. To verify, we took a look at the structually very similar `DCLP3` dataset but comes with a `InsulinPumpSettings_a` file that contians the standard basal rates. We then checked if the PumpBasalRateChange events are reported when standard basal rate change. Visually we could confirm that basal rate changes are reported when standard basal rate changes (overlapping darker scatter points).

In summary, `PEDAPTandemBASALRATECHG.txt` should contain all basal rate change events.